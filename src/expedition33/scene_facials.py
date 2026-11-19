"""Text-timed visemes and expressions on disposable, native-owned faces."""
import struct
from .story_facial import DialogueFacialPerformance,HUMAN,MOUTH
from .catalog import capture_selected,capture_matching
from .story_dialogue import identity
from ._retired_tracking import close_lease_only_scope
from .scene_visemes import SHAPES,compile_keys,encode_keys

class SceneFacials:
    def __init__(self,runtime,document):
        self.runtime=runtime;self.document=document;self.rows=[];self.closed=False;self.keys=compile_keys(document)
    def prepare(self):
        transport=self.runtime.session._session._transport
        if getattr(transport,'scene_facial_attachment_protocol',0)!=1:raise RuntimeError('Owned scene facial attachment hook required')
        keys=self.keys
        if not keys:raise ValueError('Facial dialogue requires reviewed caption phonemes')
        resources=self.runtime.session._session._story_construction_resources.resources
        human=resources.load(HUMAN,cls=True);mouth=resources.load(MOUTH)
        c=capture_matching(self.runtime.session.pid,names=('SetMorphTarget',)+tuple('head_lod0_mesh__'+name for name in SHAPES))
        function=c.find_path('/Script/Engine.SkeletalMeshComponent:SetMorphTarget')
        morphs=bytearray(6*24*16)
        active={key[2] for key in keys}
        for slot,actor in enumerate(self.document['actors']):
            if slot not in active:continue
            raw=self.runtime.registry.command(199,((88,struct.pack('<I',slot)),))
            ids=[struct.unpack_from('<iiQ',raw,at) for at in (96,112)]
            selected=capture_selected(self.runtime.session.pid,ids)
            body,face=(selected.by_index[i[0]] for i in ids)
            if any(identity(o)!=expected for o,expected in zip((body,face),ids)):raise RuntimeError('Owned facial identity changed')
            helper=DialogueFacialPerformance(self.runtime.session,identity(face))
            row=dict(name=actor['name'],helper=helper,face=face,instance=None)
            self.rows.append(row)
            helper._void(face,'/Script/Engine.SkeletalMeshComponent:SetAnimClass',NewClass=human)
            instance=helper._values(face,('AnimScriptInstance',))['AnimScriptInstance']
            if instance is None or instance.class_name!='Face_AnimBP_HumanNPC_C':raise RuntimeError('Stock face blueprint did not initialize')
            row['instance']=instance
            helper._set_scalar(face,'bPauseAnims',False)
            helper._void(face,'/Script/Engine.ActorComponent:SetComponentTickEnabled',bEnabled=True)
            # CopyPose alone supplies the head pose. The stock post-process and
            # talking gates are also required for the facial joints to articulate.
            helper._void(instance,HUMAN+':SetPostProcessAnimation')
            helper._void(face,'/Script/Engine.SkeletalMeshComponent:SetDisablePostProcessBlueprint',bInDisablePostProcess=False)
            for field,value in (('IsTalking',True),('Is in Dialogue',True),('EnvelopeVolume',.3),('EnvelopeVolumex3',.9)):
                helper._set_scalar(instance,field,value)
            with helper._call(instance,'/Script/Engine.AnimInstance:PlaySlotAnimationAsDynamicMontage',Asset=mouth,SlotNodeName='Mouth',BlendInTime=.35,BlendOutTime=.35,InPlayRate=1.,LoopCount=10000,BlendOutTriggerTime=-1.,InTimeToStartMontageAt=0.) as result:
                if result.return_value is None:raise RuntimeError('Scene mouth rig did not start')
                row['montage']=helper._hold(result.return_value)
            helper._void(instance,'/Script/Engine.AnimInstance:Montage_SetPlayRate',Montage=row['montage'],NewPlayRate=0.)
            row['slot']=slot;row['viseme']=None
            mesh=helper._values(face,('SkinnedAsset',))['SkinnedAsset']
            for shape,name in enumerate(SHAPES):
                matches=[o for o in c.objects if o.class_name=='MorphTarget' and o.name=='head_lod0_mesh__'+name and o.outer_index==mesh.index]
                if len(matches)!=1:raise ValueError('Character has no qualified facial shape: '+actor['name']+' '+name)
                struct.pack_into('<iiQ',morphs,(slot*24+shape)*16,*identity(matches[0]))
        count,encoded=encode_keys(self.document)
        self.update(0.)
        self.runtime.registry.command(200,((88,struct.pack('<iiQ',*identity(function))),(104,struct.pack('<I',count)),(112,bytes(morphs)),(2416,encoded)))
    def update(self,seconds):
        # Sample stock joint poses as well as the native morph correctives.
        # These source-clip poses are an initial visual calibration, not voice
        # alignment. The body animation remains completely independent.
        positions=(.4,.4,2.8,1.8,2.2,3.4,1.6,3.8,2.4,1.2,.8)
        for row in self.rows:
            active=next((key for key in self.keys if key[2]==row['slot'] and key[0]<=seconds<key[0]+key[1]),None)
            viseme=active[3] if active is not None else 0
            if row['viseme']==viseme:continue
            talking=viseme!=0
            if row.get('talking',True)!=talking:
                for field,value in (('IsTalking',talking),('EnvelopeVolume',.3 if talking else 0.),('EnvelopeVolumex3',.9 if talking else 0.)):
                    row['helper']._set_scalar(row['instance'],field,value)
                row['talking']=talking
            row['helper']._void(row['instance'],'/Script/Engine.AnimInstance:Montage_SetPosition',Montage=row['montage'],NewPosition=positions[viseme])
            row['viseme']=viseme
    def close(self,*,world_retired=False):
        if self.closed:return
        for row in self.rows:
            helper=row['helper']
            if helper.unknown:raise RuntimeError('Unknown facial invocation outcome; session teardown owns cleanup')
            for planner in helper.planners:planner.close()
            if not close_lease_only_scope(helper.scope):raise RuntimeError('Scene facial lease cleanup pending')
            helper.closed=True
        self.rows=[];self.closed=True

