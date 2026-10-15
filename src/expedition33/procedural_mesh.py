"""Experimental bounded static geometry; requires the mesh native candidate.

No arbitrary pointers or general dynamic array invocation exposed.
The native owner destroys the actor on transport disconnect, even if Python dies.
"""
import secrets
import struct
import threading
import math
from .catalog import capture_matching
from .values import read_values

MATERIAL_PROFILES=(('/ImagePlate/DefaultImagePlateMaterial.DefaultImagePlateMaterial', 'InputTexture', False), ('/Engine/EngineMaterials/Widget3DPassThrough_Opaque.Widget3DPassThrough_Opaque', 'SlateUI', True), ('/Engine/EngineMaterials/Widget3DPassThrough_Opaque_OneSided.Widget3DPassThrough_Opaque_OneSided', 'SlateUI', True), ('/Engine/EngineMaterials/Widget3DPassThrough_Masked.Widget3DPassThrough_Masked', 'SlateUI', True), ('/Engine/EngineMaterials/Widget3DPassThrough_Masked_OneSided.Widget3DPassThrough_Masked_OneSided', 'SlateUI', True), ('/Paper2D/DefaultSpriteMaterial.DefaultSpriteMaterial', 'SpriteTexture', False), ('/Paper2D/OpaqueUnlitSpriteMaterial.OpaqueUnlitSpriteMaterial', 'SpriteTexture', False), ('/Game/Characters/M_NPCs.M_NPCs', 'Base Color Map', False), ('/Game/Characters/M_Characters.M_Characters', 'Base Color Map', False), ('/Game/MSPresets/MS_DefaultMaterial_Displacement_00/MS_DefaultMaterial_General.MS_DefaultMaterial_General', 'Albedo', False))

MATERIAL_PROFILES += (('/Game/Characters/M_Characters1.M_Characters1','Base Color Map',True),('/Game/Characters/M_Characters_Masked.M_Characters_Masked','Base Color Map',True))

from ._material_candidates import PROFILES as LIT_CANDIDATES
MATERIAL_PROFILES += LIT_CANDIDATES

HEADER=struct.Struct('<4IQ')
IDENTITY=struct.Struct('<iiQ')
SIZE=20984
GEOMETRY=344
FUNCTIONS=(('GameplayStatics','BeginDeferredActorSpawnFromClass'),('GameplayStatics','FinishSpawningActor'),
    ('Actor','AddComponentByClass'),('Actor','FinishAddComponent'),
    ('ProceduralMeshComponent','CreateMeshSection_LinearColor'),('Actor','K2_DestroyActor'),
    ('Actor','K2_GetActorLocation'),('Actor','GetActorForwardVector'),('Actor','SetActorEnableCollision'),
    ('SceneComponent','SetMobility'),('ProceduralMeshComponent','GetNumSections'),('Actor','IsActorBeingDestroyed'))

def validate_request(data):
    if type(data) is not bytes or len(data)!=SIZE:raise ValueError('Mesh packet size')
    version,op,error,state,owner=HEADER.unpack_from(data)
    # World Builder bounded adapter; independently checked again on game thread.
    if 20 <= op <= 49:
        if version != 3 or error or state or not owner or any(data[24:88]):
            raise ValueError('Builder header')
        if op == 20:
            if any(data[2136:]): raise ValueError('Builder initialization padding')
        elif op in (30,31):
            if any(data[120:2000]) or any(data[2096:]): raise ValueError('Builder scene mutation padding')
        elif op in (33,34,40,45,46):
            if any(data[104:]): raise ValueError('Builder owned deletion padding')
        elif op in (37,38,48):
            if any(data[88:2000]) or any(data[2068:]) or struct.unpack_from('<I',data,2000)[0]>1 or any(c not in b'0123456789abcdef' for c in data[2004:2068]):raise ValueError('Builder thumbnail cache request')
        elif op == 47:
            path=data[2000:2512].split(b'\0',1)[0]
            if any(data[88:2000]) or any(data[2000+len(path):]) or not path.startswith(b'/Game/') or len(path)>=512:raise ValueError('Builder asset names request')
        elif op == 35:
            if any(data[88:2000]) or any(data[2004:]) or struct.unpack_from('<I',data,2000)[0]>250000:raise ValueError('Builder registry page')
        elif op in (21,24,42,44):
            if any(data[88:2000]) or any(data[2064:]): raise ValueError('Builder motion padding')
            if any(not math.isfinite(v) or abs(v)>(1e7 if op==42 else 10000) for v in struct.unpack_from('<8d',data,2000)):
                raise ValueError('Builder motion bounds')
        elif op == 28:
            if any(data[88:20976]) or any(data[20980:]) or struct.unpack_from('<I',data,20976)[0]>1: raise ValueError('Builder automatic flag')
        elif any(data[88:]): raise ValueError('Builder empty command payload')
        return

    if version!=3 or op not in (1,2,3,4,5,6,7,8,9,10,11,12,13) or error or state or not owner or any(data[24:88]):
        raise ValueError('Mesh request header/output fields')
    if op in (12,13):
        if any(data[88:20976]) or struct.unpack_from('<I',data,20976)[0]>(1 if op==12 else 0) or any(data[20980:]):raise ValueError('Render diagnostic payload')
        return
    if op==9:
        if any(data[344:19808]) or any(data[19904:19952]) or struct.unpack_from('<I',data,20976)[0]>4 or any(data[20980:]):raise ValueError('Skin bind payload')
        index,serial,address=IDENTITY.unpack_from(data,19808)
        if index<0 or serial<0 or not address:raise ValueError('Native hair setter identity required')
        return
    if op==8:
        if any(data[184:20976]):raise ValueError('Bone capture accepts only six identities and page')
        return
    if op not in (1,4,7) and any(data[88:19808]):raise ValueError('Cleanup/status cannot supply identities')
    if op not in (5,6,7) and any(data[19808:]):raise ValueError('Unexpected material inputs')
    if op==7 and any(data[19856:]):raise ValueError('Unexpected ground query data')
    if op!=4 and any(data[GEOMETRY:19808]):raise ValueError('Unexpected geometry')
    section,reserved=struct.unpack_from('<II',data,20976)
    if section>=64 or (reserved and (op!=5 or reserved>64)) or (op not in (5,6) and section):raise ValueError('Invalid section')
    if op==6 and any(data[19808:19952]):raise ValueError('Unexpected section identities')
    if op==4:
        nv,ni=struct.unpack_from('<II',data,GEOMETRY)
        if not 3<=nv<=256 or not 3<=ni<=768 or ni%3:raise ValueError('Geometry limits')
        for i in range(nv):
            v=struct.unpack_from('<8d',data,GEOMETRY+8+i*64)
            if any(not math.isfinite(x) or abs(x)>(10000 if j<3 else 100) for j,x in enumerate(v)):raise ValueError('Invalid vertex')
            if not .99<=sum(x*x for x in v[3:6])<=1.01:raise ValueError('Invalid normal')
        indices=struct.unpack_from('<'+str(ni)+'i',data,GEOMETRY+8+256*64)
        if any(i<0 or i>=nv for i in indices):raise ValueError('Invalid triangle')
        if any(data[GEOMETRY+8+nv*64:GEOMETRY+8+256*64]) or any(data[GEOMETRY+8+256*64+ni*4:19808]):raise ValueError('Unused geometry must be zero')

_combat_selection={}

def combat_target(pid):
    from .values import read_values_with_references
    c=capture_matching(pid,classes=('AC_jRPG_BattleManager_C','PlayerController'))
    local=[]
    for pc in c.select('PlayerController'):
        if pc.object_flags&0x30:continue
        v,c=read_values_with_references(c,pc,fields=('bIsLocalPlayerController','Pawn'))
        d={k[1]:x for k,x in v.values.items()}
        if d.get('bIsLocalPlayerController') is True and d.get('Pawn') is None:local.append(pc.index)
    targets=[]
    for m in c.select('AC_jRPG_BattleManager_C'):
        if m.object_flags&0x30 or m.outer_index not in local:continue
        v,c=read_values_with_references(c,m,fields=('CurrentCharacter','PlayerCharacters','BattleEndState'))
        d={k[1]:x for k,x in v.values.items()}
        if d.get('BattleEndState')!=0:continue
        party=tuple(getattr(d.get('PlayerCharacters'),'items',()))
        if not 1<=len(party)<=16 or any(x is None for x in party):continue
        current=d.get('CurrentCharacter')
        key=(pid,m.index,m.serial)
        previous=_combat_selection.get(key)
        fallback=next((x for x in party if (x.index,x.serial)==previous),party[0])
        target=next((x for x in party if current and (x.index,x.serial)==(current.index,current.serial)),fallback)
        _combat_selection.clear();_combat_selection[key]=(target.index,target.serial)
        targets.append((target,m))
    if len(targets)!=1:raise ValueError('No unambiguous active player combat target')
    return targets[0]

def discover(pid):
    names=tuple(dict.fromkeys(('StaticMeshActor','ProceduralMeshComponent','Default__GameplayStatics')+tuple(n for _,n in FUNCTIONS)))
    c=capture_matching(pid,names=names,classes=('PlayerController','BP_jRPG_Character_WorldMap_pawn_C','BP_jRPG_Character_World_C'))
    def one(rows):
        rows=tuple(rows)
        if len(rows)!=1:raise ValueError('Expected one live mesh prerequisite; found '+str(len(rows)))
        return rows[0]
    pc_class=c.find_class('PlayerController').index;controller=c.find_class('Controller').index
    pawns=[]
    for pc in c.select('PlayerController'):
        if pc.object_flags&0x10:continue
        values=read_values(c,pc).values
        if values.get((pc_class,'bIsLocalPlayerController')) is True:
            pawn=values.get((controller,'Pawn'))
            if pawn is not None:pawns.append(pawn)
    pawn=one(pawns) if pawns else combat_target(pid)[0]
    if pawn.class_name not in ('BP_jRPG_Character_WorldMap_pawn_C','BP_jRPG_Character_World_C') and not pawn.class_name.endswith('_Battle_C'):
        raise ValueError('Dismount and use a supported exploration character')
    ids=[pawn,one(o for o in c.objects if o.name=='Default__GameplayStatics'),
         c.by_index[c.find_class('StaticMeshActor').index],c.by_index[c.find_class('ProceduralMeshComponent').index]]
    for owner,name in FUNCTIONS:
        cls=c.find_class(owner)
        ids.append(one(o for o in c.objects if o.name==name and o.outer_index==cls.index and o.class_name=='Function'))
    return ids

class Tetrahedron:
    """One native-owned static custom model. Explicit close or scope cleanup."""
    def __init__(self,scope):
        scope._check()
        self.scope=scope;self.transport=scope._session._transport;self.pid=scope.pid
        self.owner=secrets.randbits(64) or 1
        self.closed=False;self.created=False;self.last=None
        if getattr(self.transport,'mesh_protocol',0)!=3:raise RuntimeError('Textured mesh candidate required (not RC5)')
        if not hasattr(scope,'_mesh_models'):scope._mesh_models=[]
        scope._mesh_models.append(self)

    def _command(self,op,ids=(),geometry=None,material_ids=(),texture_path=None,section_id=0,tint_gain=0):
        packet=bytearray(SIZE);struct.pack_into("<II",packet,20976,section_id,tint_gain);HEADER.pack_into(packet,0,3,op,0,0,self.owner)
        for i,obj in enumerate(ids):IDENTITY.pack_into(packet,88+16*i,obj.index,obj.serial,obj.address)
        for i,obj in enumerate(material_ids):
            if obj is not None:IDENTITY.pack_into(packet,19808+16*i,obj.index,obj.serial,obj.address)
        if texture_path:
            encoded=str(texture_path).encode('utf-16le')+b'\0\0'
            if len(encoded)>1024:raise ValueError('Texture path too long')
            packet[19952:19952+len(encoded)]=encoded
        if geometry:
            vertices,indices=geometry
            if not 3<=len(vertices)<=256 or not 3<=len(indices)<=768:raise ValueError('Geometry bounds')
            struct.pack_into('<II',packet,GEOMETRY,len(vertices),len(indices))
            for i,v in enumerate(vertices):struct.pack_into('<8d',packet,GEOMETRY+8+64*i,*v)
            struct.pack_into('<'+str(len(indices))+'i',packet,GEOMETRY+8+256*64,*indices)
        validate_request(bytes(packet))
        if op==2:
            # Scope is deliberately revoked before native cleanup starts.
            if threading.get_ident()!=self.scope._owner:raise RuntimeError('Mesh cleanup requires owner thread')
            reply=self.transport.command('mesh',bytes(packet))
        else:
            with self.scope._lease_context():reply=self.transport.command('mesh',bytes(packet))
        raw=bytes.fromhex(reply['mesh_packet'])
        echoed=(raw[120:344]==packet[120:344] and raw[352:]==packet[352:]) if op==3 else raw[88:]==packet[88:]
        if op==13:echoed=raw[88:344]==packet[88:344] and raw[19808:20976]==packet[19808:20976] and raw[20980:]==packet[20980:]
        if len(raw)!=SIZE or raw[:8]!=packet[:8] or raw[16:24]!=packet[16:24] or not echoed:
            raise RuntimeError('Mesh acknowledgement mismatch; do not retry')
        _,_,error,state,_=HEADER.unpack_from(raw)
        def identity(offset):
            index,serial,address=IDENTITY.unpack_from(raw,offset)
            return dict(index=index,serial=serial,address=hex(address),pid=self.pid,owner=self.owner)
        self.last=dict(error=error,state=state,actor=identity(24),component=identity(40),
            position=struct.unpack_from('<3d',raw,56),step=struct.unpack_from('<I',raw,80)[0],sections=struct.unpack_from('<I',raw,84)[0])
        if op==3:self.last.update(driver=identity(88),driver_asset=identity(104),switch_ms=struct.unpack_from('<I',raw,344)[0],switch_count=struct.unpack_from('<I',raw,348)[0])
        if op==13:
            count,total=struct.unpack_from('<II',raw,344);frozen=struct.unpack_from('<I',raw,20976)[0]
            if count>128 or count>total or frozen>1 or any(raw[352+count*120:16736]):raise RuntimeError('Render sample bounds')
            samples=[struct.unpack_from('<Q14d',raw,352+i*120) for i in range(count)]
            if any(not math.isfinite(v) for row in samples for v in row):raise RuntimeError('Nonfinite render sample')
            hc,ht=struct.unpack_from('<II',raw,16736)
            if hc>20 or hc>ht or any(raw[16744+hc*136:19808]):raise RuntimeError('Hair sample bounds')
            hair_samples=[struct.unpack_from('<Q16d',raw,16744+i*136) for i in range(hc)]
            if any(not math.isfinite(v) for row in hair_samples for v in row):raise RuntimeError('Hair nonfinite sample')
            self.last.update(samples=samples,total=total,frozen=bool(frozen),hair_samples=hair_samples,hair_total=ht)
        if error:raise RuntimeError('Mesh operation rejected: '+str(self.last))
        return self.last

    def spawn(self,geometry=None,ground=False):
        self.scope._check()
        if self.closed or self.created:raise RuntimeError('Use a new owner for another tetrahedron')
        ids=discover(self.scope.pid)
        ground_ids=[]
        if ground:
            if geometry:raise ValueError('Grounded catalog spawn uploads sections separately')
            c=capture_matching(self.pid,names=('Default__KismetSystemLibrary','LineTraceSingle','BreakHitResult'))
            def one(rows):
                rows=list(rows)
                if len(rows)!=1:raise ValueError('Ground query prerequisite missing/ambiguous')
                return rows[0]
            ground_ids=[one(o for o in c.objects if o.name=='Default__KismetSystemLibrary')]
            for owner,name in (('KismetSystemLibrary','LineTraceSingle'),('GameplayStatics','BreakHitResult')):
                cls=c.find_class(owner)
                ground_ids.append(one(o for o in c.objects if o.name==name and o.outer_index==cls.index and o.class_name=='Function'))
        self.created=True # uncertain failures must remain owned for cleanup
        try:return self._command(7 if ground else (4 if geometry else 1),ids,geometry,material_ids=ground_ids)
        except Exception:
            if self.last and self.last['state']==0:self.created=False
            raise

    def bind_skin(self,path,driver_index,visual_indices=None,combat_manager=None,hair_profile=0,wardrobe_menu=None):
        if type(hair_profile) is not int or not 0<=hair_profile<=4:raise ValueError("Unsupported native hair profile")
        names=('GetBoneName','GetBoneTransform','UpdateMeshSection_LinearColor','SetHiddenInGame','IsPlayerControlled','GetOwner','GetRefPoseTransform','GetBoneIndex','GetParentBone')
        owners=('SkinnedMeshComponent','SkinnedMeshComponent','ProceduralMeshComponent','SceneComponent','Pawn','ActorComponent')
        c=capture_matching(self.pid,names=names,classes=('SkinnedMeshComponent',))
        driver=c.by_index[driver_index];ids=[driver]
        for owner,name in zip(owners,names):
            rows=[o for o in c.objects if o.name==name and o.class_name=='Function' and o.outer_index==c.find_class(owner).index]
            if len(rows)!=1:raise ValueError('Rig function missing')
            ids+=rows
        if visual_indices is not None:
            if len(visual_indices)!=3 or visual_indices[0]!=driver_index:raise ValueError('Expected body, face and hair identities')
            ids.extend(c.by_index[i] for i in visual_indices)
        else:
            for name in ('Body','Face','Haircut_SkeletalMesh'):
                rows=[o for o in c.objects if o.outer_index==driver.outer_index and o.name==name]
                if len(rows)!=1:raise ValueError('Character visual component missing')
                ids+=rows
        ids.extend(c.by_index[c.find_class(n).index] for n in ('SkinnedMeshComponent','SceneComponent'))
        for name in names[6:]:
            rows=[o for o in c.objects if o.name==name and o.class_name=='Function' and o.outer_index==c.find_class('SkinnedMeshComponent').index]
            if len(rows)!=1:raise ValueError('Retarget function missing')
            ids+=rows
        if combat_manager is not None:ids.append(combat_manager)
        hc=capture_matching(self.pid,names=('K2_SetRelativeTransform','GetRelativeTransform','K2_GetComponentToWorld','K2_SetWorldTransform','SetAbsolute'))
        setter=[o for n in ('K2_SetRelativeTransform','GetRelativeTransform','K2_GetComponentToWorld','K2_SetWorldTransform','SetAbsolute') for o in hc.objects if o.name==n and o.class_name=='Function' and o.outer_index==c.find_class('SceneComponent').index]
        if len(setter)!=5:raise ValueError('Native hair fitting setter missing')
        if wardrobe_menu is not None:setter.append(wardrobe_menu)
        return self._command(9,ids,texture_path=path,material_ids=setter,section_id=hair_profile)

    def hide_driver(self):return self._command(10)

    def unbind_skin(self):return self._command(11)

    def render_probe(self,freeze=None):
        if freeze is not None:
            if type(freeze) is not bool:raise ValueError('freeze must be bool')
            self._command(12,section_id=int(freeze))
        return self._command(13)

    def status(self):
        if self.closed:return self.last
        return self._command(3) if self.created else dict(state=0)

    def set_image_plate_texture(self,catalog,texture_path,section_id=0,*,surface=False,profile=None,tint_gain=0):
        """Import a bounded PNG and attach it through the verified surface material."""
        self.scope._check()
        if self.closed or not self.created:raise RuntimeError('Spawn the model first')
        def one(rows):
            rows=list(rows)
            if len(rows)!=1:raise ValueError('Missing/ambiguous texture prerequisite')
            return rows[0]
        profile=(1 if surface else 0) if profile is None else profile
        if type(profile) is not int or not 0<=profile<len(MATERIAL_PROFILES):raise ValueError('Unknown material profile')
        if type(tint_gain) is not int or not 0<=tint_gain<=64 or (tint_gain and profile not in (1,2,3,4)):raise ValueError("Tint gain requires a Widget profile and integer 1..64")
        path,_,tinted=MATERIAL_PROFILES[profile]
        parent=catalog.find_path(path)
        ids=[parent,one(o for o in catalog.objects if o.name=='SetVectorParameterValue' and o.class_name=='Function' and o.outer_index==catalog.find_class('MaterialInstanceDynamic').index) if tinted else None,one(o for o in catalog.objects if o.name=='Default__KismetStringLibrary')]
        for owner,name in (('PrimitiveComponent','CreateDynamicMaterialInstance'),('MaterialInstanceDynamic','SetTextureParameterValue'),
                           ('MaterialInstanceDynamic','K2_GetTextureParameterValue'),('KismetStringLibrary','Conv_StringToName')):
            cls=catalog.find_class(owner)
            ids.append(one(o for o in catalog.objects if o.name==name and o.outer_index==cls.index and o.class_name=='Function'))
        ids.append(one(o for o in catalog.objects if o.name=='Default__KismetRenderingLibrary'))
        cls=catalog.find_class('KismetRenderingLibrary')
        ids.append(one(o for o in catalog.objects if o.name=='ImportFileAsTexture2D' and o.outer_index==cls.index and o.class_name=='Function'))
        return self._command(5,material_ids=ids,texture_path=texture_path,section_id=section_id,tint_gain=tint_gain)

    def upload_section(self,path,section_id):
        return self._command(6,texture_path=path,section_id=section_id)

    def close(self):
        if self.closed:return self.last
        if self.created:self._command(2)
        self.closed=True
        if self in self.scope._mesh_models:self.scope._mesh_models.remove(self)
        return self.last

    def __enter__(self):return self
    def __exit__(self,*_):self.close()


def capture_bones(scope, component_index, page=0):
    """Read at most 50 bones through verified game-thread functions."""
    scope._check()
    if type(page) is not int or not 0<=page<41:raise ValueError('Bone page')
    names=('GetNumBones','GetBoneName','GetRefPoseTransform','GetBoneTransform','GetParentBone')
    c=capture_matching(scope.pid,names=names,classes=('SkinnedMeshComponent',))
    obj=c.by_index[component_index]
    if c.find_class('SkinnedMeshComponent').index not in c.ancestors(obj.class_index):raise ValueError('Expected skinned mesh component')
    cls=c.find_class('SkinnedMeshComponent');ids=[obj]
    for name in names:
        found=[o for o in c.objects if o.name==name and o.outer_index==cls.index and o.class_name=='Function']
        if len(found)!=1:raise ValueError('Bone function missing/ambiguous')
        ids.extend(found)
    packet=bytearray(SIZE);HEADER.pack_into(packet,0,3,8,0,0,1)
    struct.pack_into('<I',packet,20976,page)
    for i,o in enumerate(ids):IDENTITY.pack_into(packet,88+i*16,o.index,o.serial,o.address)
    validate_request(bytes(packet))
    with scope._lease_context():reply=scope._session._transport.command('mesh',bytes(packet))
    raw=bytes.fromhex(reply['mesh_packet'])
    if len(raw)!=SIZE or raw[:8]!=packet[:8] or raw[88:344]!=packet[88:344] or raw[19808:]!=packet[19808:]:raise RuntimeError('Bone acknowledgement')
    error=struct.unpack_from('<I',raw,8)[0]
    if error:raise RuntimeError(f'Bone capture rejected: {error}; step {struct.unpack_from("<I",raw,80)[0]}')
    take,total=struct.unpack_from('<II',raw,344)
    if take>50 or total>2048:raise RuntimeError('Bone reply bounds')
    rows=[]
    for i in range(take):
        name,parent,*t=struct.unpack_from('<64s64s24d',raw,352+320*i)
        rows.append(dict(index=page*50+i,name=name.split(b'\0')[0].decode('ascii'),parent=parent.split(b'\0')[0].decode('ascii'),reference=t[:12],world=t[12:]))
    return dict(component=component_index,total=total,bones=rows)
