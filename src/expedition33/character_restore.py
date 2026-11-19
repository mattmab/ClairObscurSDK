"""Preserve a character's skills and appearance around original definition refresh.

Native operation 261 reads the current configured graph when it already exists,
otherwise an original, retained read of the selected native save file. No unlock list is accepted from
Python. Appearance comes from current CharacterData, with missing fields filled
from the same validated checkpoint. Uncertain dispatches retain their owner and
are never replayed.
"""
import struct
from .story_original import _Owner
from ._story_original_wire import put_id,identity,OriginalNarrativeError

SIZE=20984
COUNT=10
LEASES=184
GUID=264
MODE=280
DIAGNOSTICS=284
SLOT=300
FILE_COUNT=304
FILE=308
PROFILE=828
TAIL=5384
from ._character_restore_profile import encode as encode_profile,decode as decode_profile
CHARACTER='/Game/Gameplay/CharacterData/BP_CharacterData.BP_CharacterData_C'
SYSTEM='/Game/Gameplay/SkillTree/BP_CharacterSkillGraphSystem.BP_CharacterSkillGraphSystem_C'
STRUCT='/Game/jRPGTemplate/Structures/S_jRPG_CharacterSaveState.S_jRPG_CharacterSaveState'
SAVE_MANAGER='/Game/Gameplay/Save/BP_SaveManager.BP_SaveManager_C'
SAVE_PATH=SAVE_MANAGER+':ComputeSaveFilePath'
LOAD_FILE='/Script/Engine.GameplayStatics:LoadGameFromSlot'
STATICS='/Script/Engine.Default__GameplayStatics'
FUNCTIONS=(CHARACTER+':LoadCharacterBaseDataFromID',SYSTEM+':LoadCharacterState',SYSTEM+':EquipSkillAtSlot',
 CHARACTER+':SetCharacterCustomizationItemData',CHARACTER+':LoadCharacterCustomizationFromItemData')
DEPENDENCIES=(*FUNCTIONS[:3],STRUCT,*FUNCTIONS[3:])
FILE_DEPENDENCIES=(SAVE_PATH,LOAD_FILE,STATICS)

class _RestorePreparation:
    """Process-owned immutable metadata; never a save, manager, or party actor."""
    def __init__(self,resources):
        from .catalog import capture_matching,capture_selected
        from .reflection import describe_selected
        from .story_dialogue import identity as object_identity
        self.resources=resources;self.session=resources.scope._session;self.held={}
        catalog=capture_matching(resources.scope.pid,names=(*(path.rsplit(':',1)[1] for path in FUNCTIONS),
            'S_jRPG_CharacterSaveState','ComputeSaveFilePath','LoadGameFromSlot','Default__GameplayStatics'))
        for path in (*DEPENDENCIES,*FILE_DEPENDENCIES):self.held[path]=resources.hold(catalog.find_path(path))
        # Include every referenced type (also non-parameter Blueprint locals),
        # exactly as the cold planner does. CDO and all functions stay leased.
        snapshot=describe_selected(resources.scope.pid,tuple(object_identity(self.held[p].object) for p in FILE_DEPENDENCIES[:2]))
        selected=capture_selected(resources.scope.pid,tuple(object_identity(h.object) for h in self.held.values()))
        with resources.scope.invocation_planner(catalog=snapshot.catalog.with_observations(selected),selected_results=True) as planner:
            planner._metadata.read('struct',snapshot.catalog,tuple(d.object for d in snapshot.descriptors.values()),lambda catalog,objects:snapshot.descriptors)
            self.observations=planner.observations()
    def check(self,scope):
        self.resources.scope._check();scope._check()
        if scope._session is not self.session or any(not h.active for h in self.held.values()):
            raise RuntimeError('Character restore metadata ownership changed')
    def file_planner(self,scope,manager,*,observed=None):
        from .catalog import capture_selected
        from .story_dialogue import identity as object_identity
        self.check(scope)
        planner=scope.invocation_planner(observations=self.observations,selected_results=True)
        try:
            fresh=observed if observed is not None else capture_selected(scope.pid,(object_identity(manager),))
            current=fresh.by_index[manager.index]
            if (fresh.pid!=scope.pid or object_identity(current)!=object_identity(manager) or
                    current.object_flags&0x30 or current.class_name!='BP_SaveManager_C'):
                raise RuntimeError('Selected save manager lease observation changed')
            planner.adopt_observations(fresh)
        except BaseException:planner.close();raise
        return planner

def warm(resources):
    """Warm retained restore metadata at title without reading a selected save.

    Every native restoration still validates the current save, actor, graph,
    appearance, and full function schemas. Failed preparation is journaled and
    cannot silently replay a potentially uncertain lease acquisition.
    """
    resources.scope._check()
    journal=getattr(resources,'_character_restore_preparation',None)
    if journal is not None:
        if not journal['ready']:raise RuntimeError('Incomplete Character restore metadata preparation remains owned; restart required')
        journal['value'].check(resources.scope);return journal['value']
    journal={'ready':False,'value':None,'error':None};resources._character_restore_preparation=journal
    try:
        journal['value']=_RestorePreparation(resources);journal['ready']=True
        return journal['value']
    except BaseException as error:journal['error']=str(error);raise

def _file_call_catalog(pid,manager,dependencies):
    """Selected call targets plus all reflected types, including BP locals.

    ComputeSaveFilePath has a non-parameter PlatformsSubsystem local. The strict
    planner validates that local too, so selecting only function ancestry is
    insufficient. These are fresh bounded observations, never dispatch grants.
    """
    from .catalog import capture_selected
    from .reflection import describe_selected
    from .story_dialogue import identity as object_identity
    catalog=capture_selected(pid,tuple(object_identity(obj) for obj in (manager,*(held.object for held in dependencies))))
    metadata=describe_selected(pid,tuple(object_identity(held.object) for held in dependencies[:2]))
    return catalog.with_observations(metadata.catalog)

def packet(owner,objects,key,mode=0,*,profile,slot=-1,filename=None):
    data=bytearray(SIZE);struct.pack_into('<4IQ',data,0,5,261,0,0,owner)
    if len(objects)!=COUNT or len(key)!=32:raise ValueError('Ten exact Character restore dependencies and selected-save key required')
    for i,obj in enumerate(objects):put_id(data,24+i*16,obj.object)
    struct.pack_into('<10Q',data,LEASES,*(o._token for o in objects))
    struct.pack_into('<4II',data,GUID,*(int(key[i:i+8],16) for i in range(0,32,8)),mode)
    encoded=(filename.encode('utf-16-le')+b'\0\0') if type(filename)is str and filename and '\0' not in filename else b''
    if filename is not None and (not encoded or len(encoded)>520):raise ValueError('Selected native filename is invalid')
    struct.pack_into('<iI',data,SLOT,slot,len(encoded)//2);data[FILE:FILE+len(encoded)]=encoded
    data[PROFILE:TAIL]=encode_profile(profile)
    result=bytes(data);validate(result);return result

def validate(data):
    if type(data)is not bytes or len(data)!=SIZE or struct.unpack_from('<4I',data)!=(5,261,0,0) or not struct.unpack_from('<Q',data,16)[0]:raise ValueError('Character restore packet header')
    for at in range(24,LEASES,16):identity(data,at)
    if not all(struct.unpack_from('<10Q',data,LEASES)) or struct.unpack_from('<I',data,GUID)[0]!=0xe33c5701 or struct.unpack_from('<I',data,MODE)[0]>2 or any(data[DIAGNOSTICS:SLOT]) or any(data[TAIL:]):raise ValueError('Character restore ownership or padding')
    decode_profile(data[PROFILE:TAIL])
    slot,count=struct.unpack_from('<iI',data,SLOT)
    if count==0:
        if slot!=-1 or any(data[FILE:PROFILE]):raise ValueError('Live graph repair cannot select a save file')
    elif not 0<=slot<32 or not 2<=count<=260 or any(data[FILE+count*2-2:PROFILE]):raise ValueError('Selected file extent is invalid')
    elif any(struct.unpack_from('<H',data,FILE+i*2)[0]==0 for i in range(count-1)):raise ValueError('Selected file contains a terminator')

def decode(sent,reply):
    validate(sent)
    if type(reply)is not bytes or len(reply)!=SIZE:raise RuntimeError('Character restore acknowledgement size')
    clean=bytearray(reply);clean[8:16]=sent[8:16];clean[DIAGNOSTICS:SLOT]=sent[DIAGNOSTICS:SLOT]
    if bytes(clean)!=sent:raise RuntimeError('Character restore acknowledgement context changed')
    error,state=struct.unpack_from('<2I',reply,8)
    stage,source,unlocked,equipped=struct.unpack_from('<4I',reply,DIAGNOSTICS)
    if error:
        failure=OriginalNarrativeError(error,reason=f'stage={stage}, source={source}, unlocked={unlocked}, equipped={equipped}')
        failure.diagnostics=dict(stage=stage,source=source,unlocked=unlocked,equipped=equipped)
        raise failure
    mode=struct.unpack_from('<I',sent,MODE)[0]
    if state!=mode+1:raise RuntimeError('Character restore acknowledgement state')
    if mode!=2 and (stage!=20 or source not in (1,2) or not 1<=unlocked<=len(decode_profile(sent[PROFILE:TAIL])['skills']) or not 0<=equipped<=6):raise RuntimeError('Character restore acknowledgement incomplete')
    return dict(stage=stage,source='saved-state' if source==1 else 'live-graph' if source==2 else None,unlocked=unlocked,equipped=equipped)

class CharacterRestore(_Owner):
    def __init__(self,parent,key,*,resources,profile):
        self.profile=decode_profile(encode_profile(profile))
        if type(getattr(parent._session._transport,'character_restore_protocol',None))is not int or parent._session._transport.character_restore_protocol!=5:raise RuntimeError('Character skill/appearance-preserving refresh requires SDK character restore capability5')
        super().__init__(parent,key,resources=resources);self.attempted=False;self.receipt=None;self.slot=-1;self.filename=None;self.file_result=None
    def prepare(self,actor):
        if self.attempted or self.started or self.held:raise RuntimeError('Character skill restoration is one-shot')
        from ._stable_lease import acquire_stable
        from ._reader import shared_operation
        with shared_operation(self.scope.pid):
            gi=self.hold(self.resources.gi)
            character,_=acquire_stable(self.scope,actor);self.held.append(character)
            graph=self.hold(self.resources.load(self.profile['graph']))
            prepared=warm(self.resources);prepared.check(self.scope)
            dependencies=tuple(self.hold(prepared.held[path].object) for path in DEPENDENCIES)
            observed=self._values(character.object,('HardcodedNameID','SkillGraph'))
            from .story_dialogue import identity as object_identity
            if observed['HardcodedNameID']!=self.profile['character']:raise RuntimeError('Selected character does not match the profile')
            if object_identity(observed['SkillGraph'])==object_identity(graph.object):source=graph
            else:source=self._read_file(gi.object,preparation=prepared)
            self.objects=(gi,character,graph,*dependencies[:4],source,*dependencies[4:])
            self.attempted=True;self.receipt=self.send(0);self.started=True
        return self
    def _values(self,obj,fields):
        from .values import capture_selected_values
        from .story_dialogue import identity as object_identity,field
        catalog,rows=capture_selected_values(self.scope.pid,(object_identity(obj),),fields=fields,references=True)
        current=catalog.by_index[obj.index];row=rows[obj.index]
        if object_identity(current)!=object_identity(obj) or current.object_flags&0x30 or row.errors or row.truncated:raise RuntimeError('Selected save observation changed or is incomplete')
        return {name:field(row,name) for name in fields}
    def _file_context(self,gi,manager=None):
        from .story_dialogue import identity as object_identity
        if manager is None:
            data=self._values(gi,('SaveManager','LastRelevantSaveName'))
            manager=data['SaveManager']
            if manager is None or manager.class_name!='BP_SaveManager_C':raise RuntimeError('Selected native save file is unavailable')
            state=self._values(manager,('GameInstanceReference','SelectedSlot','LoadIsInProgress','SaveIsInProgress'))
        else:
            # After the original file read the expected manager is already
            # leased. Observe it and GI together, then prove GI still points to
            # that exact manager. No pre-dispatch values or slot are reused.
            from .values import capture_selected_values
            from .story_dialogue import field
            fields=('SaveManager','LastRelevantSaveName','GameInstanceReference','SelectedSlot','LoadIsInProgress','SaveIsInProgress')
            catalog,rows=capture_selected_values(self.scope.pid,(object_identity(gi),object_identity(manager)),fields=fields,references=True)
            for obj in (gi,manager):
                current=catalog.by_index[obj.index];row=rows[obj.index]
                if object_identity(current)!=object_identity(obj) or current.object_flags&0x30 or row.errors or row.truncated:
                    raise RuntimeError('Selected save observation changed or is incomplete')
            data={name:field(rows[gi.index],name) for name in fields[:2]}
            state={name:field(rows[manager.index],name) for name in fields[2:]}
            if object_identity(data['SaveManager'])!=object_identity(manager) or manager.class_name!='BP_SaveManager_C':
                raise RuntimeError('Selected native save manager changed during its original file read')
        filename=data['LastRelevantSaveName']
        if type(filename)is not str or not filename or '\0' in filename or len(filename.encode('utf-16-le'))>518:raise RuntimeError('Selected native save file is unavailable')
        slot=state['SelectedSlot']
        if object_identity(state['GameInstanceReference'])!=object_identity(gi) or type(slot)is not int or not 0<=slot<32 or state['LoadIsInProgress'] is not False or state['SaveIsInProgress'] is not False:raise RuntimeError('Selected save manager is busy or belongs to another game instance')
        return manager,slot,filename
    def _read_file(self,gi,catalog=None,*,preparation=None):
        from ._stable_lease import acquire_stable
        from .story_dialogue import identity as object_identity
        before=self._file_context(gi);manager,self.slot,self.filename=before
        manager_lease,manager_catalog=acquire_stable(self.scope,manager);self.held.append(manager_lease);manager=manager_lease.object
        if preparation is not None:
            preparation.check(self.scope)
            dependencies=tuple(self.hold(preparation.held[path].object) for path in FILE_DEPENDENCIES)
            planner=preparation.file_planner(self.scope,manager,observed=manager_catalog)
        else:
            dependencies=tuple(self.hold(catalog.find_path(path)) for path in FILE_DEPENDENCIES)
            catalog=_file_call_catalog(self.scope.pid,manager,dependencies)
            planner=self.scope.invocation_planner(catalog=catalog,selected_results=True)
        try:
            path_call=planner.prepare(manager,dependencies[0].object,SaveName=self.filename)
            self.attempted=True
            try:
                with path_call.invoke() as result:filepath=result.return_value
                if type(filepath)is not str or not filepath or '\0' in filepath or len(filepath.encode('utf-16-le'))>8190:raise RuntimeError('Original save path conversion returned an invalid filename')
                load_call=planner.prepare(dependencies[2].object,dependencies[1].object,SlotName=filepath,UserIndex=0)
                self.file_result=load_call.invoke(fresh_results=True)
                loaded=self.file_result.return_value
                if loaded is None or loaded.class_name!='BP_SaveGameObject_V8_C':raise RuntimeError('Original selected save read did not return the qualified native version')
                source=self._file_source_lease(loaded);self.held.append(source)
                after=self._file_context(gi,manager)
                if (object_identity(after[0]),after[1:])!=(object_identity(manager),before[1:]):raise RuntimeError('Selected native save changed during its original file read')
                return source
            except BaseException as error:
                from .invocation import InvocationError
                if not isinstance(error,InvocationError) or error.outcome!='not_dispatched':self.unknown=True
                raise
        finally:planner.close()
    def _file_source_lease(self,loaded):
        """Borrow the exact retained output, without transferring its owner.

        The result remains active until native restoration cleanup succeeds.
        No fallback lease acquisition is allowed if that ownership is unclear.
        """
        from .story_dialogue import identity as object_identity
        result=self.file_result
        if (result is None or result.active is not True or result._scope is None or
                result._scope() is not self.scope or result._session() is not self.scope._session or
                len(result._leases)!=1):
            raise RuntimeError('Original save result does not own one active scoped output')
        lease=result._leases[0]
        if (lease.active is not True or lease._scope is None or lease._scope() is not self.scope or
                lease._session() is not self.scope._session or not lease._token or
                object_identity(lease.object)!=object_identity(loaded) or loaded.serial<=0):
            raise RuntimeError('Original save output lease ownership changed')
        return lease
    def send(self,mode):
        sent=packet(self.owner,self.objects,self.key,mode,profile=self.profile,slot=getattr(self,'slot',-1),filename=getattr(self,'filename',None))
        try:return decode(sent,bytes.fromhex(self.scope._session._transport.command('mesh',sent)['mesh_packet']))
        except OriginalNarrativeError as error:
            self.diagnostics=getattr(error,'diagnostics',None)
            if error.code==4301:self.unknown=True
            raise
        except BaseException:self.unknown=True;raise
    def close(self):
        if self.closed:return True
        if self.unknown:return False
        if self.started:self.send(2);self.started=False
        result=getattr(self,'file_result',None)
        if result is not None:
            if not result.release():return False
            self.file_result=None
        self.scope.close();self.closed=True;return True
