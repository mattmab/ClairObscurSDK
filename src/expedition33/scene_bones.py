"""Bounded sampled body motion on the Scene Editor's disposable Sophie actor."""
import math,struct
from .catalog import capture_matching,capture_selected
from .reflection import describe_selected
from .enums import describe_enums
from .story_dialogue import identity
from .story_facial import DialogueFacialPerformance

def validate_motion(document):
    row=document.get('bone_motion')
    if row is None:return None
    if type(row) is not dict or set(row)!={'actor','hold','end','motion'}:raise ValueError('Bone performance fields')
    actors=[i for i,a in enumerate(document['actors']) if a['id']==row['actor'] and a['assembly']=='mesh-4139998eb15a']
    if len(actors)!=1:raise ValueError('Bone performance requires the qualified Sophie assembly')
    h,e=row['hold'],row['end']
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in (h,e)) or not 0<=h<e<=document['duration']:raise ValueError('Bone performance timing')
    m=row['motion']
    if type(m) is not dict or set(m)!={'format','version','source','duration','fps','bones','frames'} or m['format']!='e33.bone-motion' or m['version']!=1:raise ValueError('Bone motion format')
    if type(m['source']) is not str or not m['source'].startswith('/Game/'):raise ValueError('Bone motion provenance')
    if type(m['fps']) not in (int,float) or not math.isfinite(m['fps']) or not 1<=m['fps']<=60:raise ValueError('Bone motion frame rate')
    bones,frames=m['bones'],m['frames']
    if type(bones) is not list or not 1<=len(bones)<=384 or type(frames) is not list or not 1<=len(frames)<=96:raise ValueError('Bone motion bounds')
    names=set();indices=set()
    for b in bones:
        if type(b) is not dict or set(b)!={'name','index'} or type(b['name']) is not str or not 1<=len(b['name'])<=63 or not b['name'].isascii() or b['name'] in names or type(b['index']) is not int or not 0<=b['index']<8192 or b['index'] in indices:raise ValueError('Bone mapping')
        names.add(b['name']);indices.add(b['index'])
    for i,f in enumerate(frames):
        if type(f) is not dict or set(f)!={'at','poses'} or type(f['at']) not in (int,float) or not math.isfinite(f['at']) or abs(f['at']-i/m['fps'])>.01 or type(f['poses']) is not list or len(f['poses'])!=len(bones):raise ValueError('Bone frame layout')
        for p in f['poses']:
            if type(p) is not list or len(p)!=10 or any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>1e6 for v in p) or abs(sum(v*v for v in p[:4])-1)>1e-4 or any(v<=0 for v in p[7:]):raise ValueError('Bone pose values')
    if type(m['duration']) not in (int,float) or not math.isfinite(m['duration']) or abs(m['duration']-frames[-1]['at'])>.01:raise ValueError('Bone duration')
    return actors[0],row

def validate_wire(data):
    op=struct.unpack_from('<I',data,4)[0]
    if op==203:
        for at in (88,104,120,136,152,168):
            i,s,a=struct.unpack_from('<iiQ',data,at)
            if i<0 or s<0 or not a:raise ValueError('Bone import identity')
        if struct.unpack_from('<I',data,184)[0]>=6 or any(data[188:]):raise ValueError('Bone import slot')
    elif op==201:
        for at in (88,104,120,136,152):
            i,s,a=struct.unpack_from('<iiQ',data,at)
            if i<0 or s<0 or not a:raise ValueError('Bone owner identity')
        slot,frames,bones,reserved=struct.unpack_from('<4I',data,168);hold,end,fps=struct.unpack_from('<ddf',data,184)
        if slot>=6 or not 1<=frames<=96 or not 1<=bones<=384 or reserved or any(data[204:208]) or any(data[208+bones*4:]) or any(not math.isfinite(v) for v in (hold,end,fps)) or not 0<=hold<end<=120 or not 1<=fps<=60:raise ValueError('Bone configure packet')
        ids=struct.unpack_from('<'+str(bones)+'I',data,208)
        if len(set(ids))!=bones or any(i>=8192 for i in ids):raise ValueError('Bone index table')
    elif op==202:
        slot,frame,bones,reserved=struct.unpack_from('<4I',data,88)
        if slot>=6 or frame>=96 or not 1<=bones<=384 or reserved or any(data[104+bones*40:]):raise ValueError('Bone frame packet')
        for i in range(bones):
            p=struct.unpack_from('<10f',data,104+i*40)
            if any(not math.isfinite(v) or abs(v)>1e6 for v in p) or abs(sum(v*v for v in p[:4])-1)>1e-4 or any(v<=0 for v in p[7:]):raise ValueError('Bone frame transform')
    else:raise ValueError('Bone operation')

class _Calls(DialogueFacialPerformance):
    def _call(self,obj,path,**arguments):
        key=(identity(obj),path)
        if key in self.calls:return super()._call(obj,path,**arguments)
        c=capture_matching(self.scope.pid,names=(path.rsplit(':',1)[-1],'Transform','Quat','Vector'))
        c=c.with_observations(capture_selected(self.scope.pid,tuple([identity(obj)]+[identity(v) for v in arguments.values() if hasattr(v,'class_index')])))
        fn=c.find_path(path);c=c.with_observations(describe_selected(self.scope.pid,(identity(fn),)).catalog)
        planner=self.scope.invocation_planner(catalog=c,selected_results=True);self.planners.append(planner)
        call=planner.prepare(c.by_index[obj.index],c.find_path(path),**arguments);self.calls[key]=call;self.unknown=True
        try:result=call.invoke()
        except Exception as error:
            if getattr(error,'outcome',None)=='not_dispatched':self.unknown=False
            raise
        self.unknown=False;return result

class SceneBones:
    def __init__(self,runtime,document):
        self.runtime=runtime;self.document=document;self.helper=None;self.closed=False;self.body=None;self.cloth_active=None;self.cloth_old=None
    def prepare(self):
        if getattr(self.runtime.session._session._transport,'scene_bone_timeline_protocol',0)!=1:raise RuntimeError('Native bone timeline SDK hook required')
        slot,row=validate_motion(self.document);motion=row['motion']
        raw=self.runtime.registry.command(199,((88,struct.pack('<I',slot)),))
        body_id=struct.unpack_from('<iiQ',raw,96);c=capture_selected(self.runtime.session.pid,(body_id,));body=c.by_index[body_id[0]]
        actor=c.by_index[body.outer_index];helper=self.helper=_Calls(self.runtime.session,identity(actor))
        if not self.document.get('facial_dialogue',False):
            from .story_facial import HUMAN
            face_id=struct.unpack_from('<iiQ',raw,112);face=capture_selected(self.runtime.session.pid,(face_id,)).by_index[face_id[0]]
            human=self.runtime.session._session._story_construction_resources.resources.load(HUMAN,cls=True)
            helper._void(face,'/Script/Engine.SkeletalMeshComponent:SetAnimClass',NewClass=human)
            helper._void(face,'/Script/Engine.SkeletalMeshComponent:SetDisablePostProcessBlueprint',bInDisablePostProcess=False)
            helper._set_scalar(face,'bPauseAnims',False)
            helper._void(face,'/Script/Engine.ActorComponent:SetComponentTickEnabled',bEnabled=True)
        c=capture_matching(self.runtime.session.pid,names=('ControlRigComponent','FKControlRig','Default__metahuman_proc_ControlRig_C','EControlRigComponentMapDirection','SetLocalTransformByIndex','SetComponentTickEnabled'))
        component_class=c.find_path('/Script/ControlRig.ControlRigComponent');rig_class=c.find_path('/Script/ControlRig.FKControlRig')
        template=c.find_path('/Game/MetaHumans/Common/Common/metahuman_proc_ControlRig.Default__metahuman_proc_ControlRig_C')
        enum=c.find_path('/Script/ControlRig.EControlRigComponentMapDirection');direction=describe_enums(c,(enum,))[enum.index].value('EControlRigComponentMapDirection::Output')
        setter=helper._hold(c.find_path('/Script/ControlRig.RigHierarchy:SetLocalTransformByIndex'));tick=helper._hold(c.find_path('/Script/Engine.ActorComponent:SetComponentTickEnabled'))
        source=helper._hold(helper._values(template,('DynamicHierarchy',))['DynamicHierarchy'])
        with helper._call(body,'/Script/Engine.SceneComponent:GetRelativeTransform') as result:relative=result.return_value
        with helper._call(actor,'/Script/Engine.Actor:AddComponentByClass',Class=component_class,bManualAttachment=False,RelativeTransform=relative,bDeferredFinish=False) as result:self.component=helper._hold(result.return_value)
        helper._void(self.component,'/Script/Engine.ActorComponent:SetComponentTickEnabled',bEnabled=False)
        helper._void(self.component,'/Script/ControlRig.ControlRigComponent:SetControlRigClass',InControlRigClass=rig_class)
        helper._void(self.component,'/Script/ControlRig.ControlRigComponent:Initialize')
        with helper._call(self.component,'/Script/ControlRig.ControlRigComponent:GetControlRig') as result:rig=helper._hold(result.return_value)
        hierarchy=helper._hold(helper._values(rig,('DynamicHierarchy',))['DynamicHierarchy'])
        helper._void(hierarchy,'/Script/ControlRig.RigHierarchy:CopyHierarchy',InHierarchy=source)
        with helper._call(hierarchy,'/Script/ControlRig.RigHierarchy:GetController',bCreateIfNeeded=True) as result:controller=helper._hold(result.return_value)
        mesh=helper._values(body,('SkinnedAsset',))['SkinnedAsset'];skeleton=helper._hold(helper._values(mesh,('Skeleton',))['Skeleton'])
        functions=capture_matching(self.runtime.session.pid,names=('ImportBones',));importer=helper._hold(functions.find_path('/Script/ControlRig.RigHierarchyController:ImportBones'))
        packed=b''.join(struct.pack('<iiQ',*identity(v)) for v in (self.component,rig,hierarchy,controller,importer,skeleton))
        self.runtime.registry.command(203,((88,packed),(184,struct.pack('<I',slot))))
        helper._void(self.component,'/Script/ControlRig.ControlRigComponent:AddMappedCompleteSkeletalMesh',SkeletalMeshComponent=body,InDirection=direction)
        helper._set_scalar(self.component,'bResetTransformBeforeTick',True)
        helper._set_scalar(self.component,'bEnableLazyEvaluation',False)
        self.body=helper._hold(body)
        self.cloth_old=helper._values(body,('ClothBlendWeight','bDisableClothSimulation','bDisablePostProcessBlueprint'))
        self._cloth(True)
        helper._set_scalar(body,'bPauseAnims',False)
        helper._void(body,'/Script/Engine.ActorComponent:SetComponentTickEnabled',bEnabled=True)
        # Check every authored mapping against this actual disposable component.
        from .values import read_values_with_references
        c=capture_selected(self.runtime.session.pid,(identity(self.component),));values,_=read_values_with_references(c,c.by_index[self.component.index],fields=('MappedElements',))
        array=next(iter(values.values.values()))
        if values.errors or values.truncated or len(array.items)!=array.length:raise RuntimeError('Complete owned rig mapping required')
        mapping={v.fields['ElementName']:v.fields['ElementIndex'] for v in array.items}
        if any(b['name'] not in mapping for b in motion['bones']):raise RuntimeError('Authored motion does not match the owned rig hierarchy')
        ids=b''.join(struct.pack('<iiQ',*identity(v)) for v in (setter,self.component,rig,hierarchy,tick))
        indices=struct.pack('<'+str(len(motion['bones']))+'I',*(mapping[b['name']] for b in motion['bones']))
        self.runtime.registry.command(201,((88,ids),(168,struct.pack('<4Iddf',slot,len(motion['frames']),len(motion['bones']),0,row['hold'],row['end'],motion['fps'])),(208,indices)))
        for i,frame in enumerate(motion['frames']):
            packed=struct.pack('<'+str(len(motion['bones'])*10)+'f',*(v for pose in frame['poses'] for v in pose))
            self.runtime.registry.command(202,((88,struct.pack('<4I',slot,i,len(motion['bones']),0)),(104,packed)))
    def _cloth(self,active):
        if self.cloth_active==active:return
        self.helper._set_scalar(self.body,'ClothBlendWeight',0. if active else self.cloth_old['ClothBlendWeight'])
        self.helper._set_scalar(self.body,'bDisableClothSimulation',True if active else self.cloth_old['bDisableClothSimulation'])
        self.helper._void(self.body,'/Script/Engine.SkeletalMeshComponent:SetDisablePostProcessBlueprint',bInDisablePostProcess=True if active else self.cloth_old['bDisablePostProcessBlueprint'])
        self.cloth_active=active
    def update(self,seconds):
        if not self.closed and self.body is not None:self._cloth(seconds<self.document['bone_motion']['end'])
    def close(self,*,world_retired=False):
        if self.closed:return True
        if self.helper is not None and not self.helper.close(world_retired=world_retired):return False
        self.closed=True;return True
