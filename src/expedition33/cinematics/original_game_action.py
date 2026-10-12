"""Mapped original game-action playback with fresh travel-context validation.

The game owns cinematic actors, cameras and audio. SDK menu disposal does not
stop a running original action; native Stop is not exposed by this adapter.
"""

from expedition33 import _query,RuntimeQueryError
from expedition33.catalog import capture_matching
from expedition33.cinematics.history import read_current_history
from expedition33._scope import SessionScope
from expedition33._reader import ReadBatch
from expedition33.assets import load_asset
from expedition33.catalog import capture_selected
from expedition33.values import read_object_reference,read_values
import json,re,time,logging
from pathlib import Path

WORLD = '/Game/Levels/OrangeForest/Level_OraneForest_Main.Level_OraneForest_Main'
ASSET = '/Game/Levels/OrangeForest/GameActions/DA_GA_CIN_MCS_ScavengerIntro.DA_GA_CIN_MCS_ScavengerIntro'
SAVE_ID = 'Cine_ScavengerIntro_Orange'
DEFINITION='Sandfall/Content/Levels/OrangeForest/GameActions/DA_GA_CIN_MCS_ScavengerIntro.uasset'
SEQUENCE='/Game/Cinematics/OrangeForest/CS_OrangeForest_ScavengerIntro.CS_OrangeForest_ScavengerIntro'
SHA256='269cd1e6ec20415ffc70b613288d7b9650faad0ea43ab7c9be8d1855d8006ea3'

class NotReady(RuntimeError):pass

def controller_context(session):
    """Fresh persistent LocalPlayer reference, not an enumerated old controller."""
    try:return _controller_context_once(session)
    except RuntimeQueryError as error:
        if str(error)=='Object identity changed or belongs to another process':
            # All observations above are discarded. The next bounded poll starts
            # from a fresh catalog; this never retries a mutation or invocation.
            raise NotReady('controller_context: '+str(error)) from error
        raise

def _controller_context_once(session):
    catalog=capture_matching(session.pid,classes=('LocalPlayer',))
    rows=tuple(o for o in catalog.objects if o.class_name=='LocalPlayer' and not o.object_flags&0x30)
    if not rows:raise NotReady('Local player is not available yet')
    local=_one(rows)
    observed=read_values(catalog,local)
    owner=catalog.by_index[_one(key[0] for key in observed.types if key[1]=='PlayerController')]
    player,catalog=read_object_reference(catalog,local,owner,'PlayerController')
    if player is None:raise NotReady('Player controller is not available yet')
    worlds=tuple(o for o in catalog.outer_chain(player) if o.class_name=='World')
    if not worlds:raise NotReady('Controller world is not available yet')
    world=_one(worlds)
    return dict(controller=(player.pid,player.index,player.serial,player.address),world=(world.pid,world.index,world.serial,world.address),world_path=catalog.path_name(world))

def ready_history(session):
    try:return read_current_history(session)
    except RuntimeQueryError as error:
        if str(error)=='Object identity changed or belongs to another process':
            raise NotReady('history_context: '+str(error)) from error
        raise
    except RuntimeError as error:
        # Only known transient loading states are retryable. Decoder/schema and
        # identity validation errors remain terminal and visible.
        if str(error) in ('A save load is in progress','Current game history has no loaded save context','Current history context reference is null'):
            raise NotReady(str(error)) from error
        raise

def matches(scene):
    return (scene.get('id')==DEFINITION and scene.get('saved_id')==SAVE_ID and
            scene.get('sequence')==SEQUENCE and scene.get('sha256',scene.get('definition_sha256'))==SHA256)


def _one(rows):
    rows = tuple(rows)
    if len(rows) != 1:
        raise RuntimeError('Expected one current native replay identity')
    return rows[0]


def _values(obj):
    _, rows = _query(['--read-values', str(obj.pid), f'{obj.index}:{obj.serial}:{obj.address:x}'])
    return rows


def _field(rows, name):
    row = _one(r for r in rows if r.get('name') == name and
               r.get('event') in ('stored_value', 'stored_value_error'))
    if row['event'] != 'stored_value':
        raise RuntimeError('Unreadable native replay state: ' + name)
    return row['value']


def _read_action_preflight(session,profile):
    current_context=controller_context(session)
    catalog = capture_matching(session.pid, names=('ExecuteGameAction', 'DA_GA_CIN_MCS_ScavengerIntro',
        'GameAction', 'GameActionInstance'), classes=('BP_GameActionExecutorComponent_C', 'BP_CinematicSystem_C'))
    prefix = profile['world_path'] + ':PersistentLevel.'
    executors=tuple(o for o in catalog.objects if o.class_name=='BP_GameActionExecutorComponent_C' and catalog.path_name(o).startswith(prefix) and not o.object_flags&0x30)
    if not executors:raise NotReady('Destination cinematic executor is not initialized yet')
    executor=_one(executors)
    component = _one(o for o in catalog.objects if o.class_name == 'BP_CinematicSystem_C'
                     and o.outer_index == executor.outer_index and not o.object_flags & 0x30)
    world = _one(o for o in catalog.outer_chain(executor) if catalog.path_name(o) == profile['world_path'])
    if (world.pid, world.index, world.serial, world.address) != current_context['world']:
        raise RuntimeError('Scavenger executor is not in the active loaded world')
    function = _one(o for o in catalog.objects if o.class_name == 'Function'
                    and o.name == 'ExecuteGameAction' and o.outer_index == executor.class_index)
    active = _field(_values(executor), 'GameActionInstancesInExecution')
    if active != {'$array': {'length': 0, 'items': []}}:
        raise NotReady('A game action is already executing')
    current = _values(component)
    for name in ('LevelSequencePlayer', 'LoadCinematicAssetRequest'):
        if _field(current, name) is not None:
            raise NotReady('A native cinematic is already active or preparing')
    return catalog,executor,component,function,current_context


def prepare(session,scene,profile=None):
    session._check()
    profile=profile or dict(id=DEFINITION,saved_id=SAVE_ID,sequence=SEQUENCE,definition_sha256=SHA256,world_path=WORLD,action_path=ASSET)
    if not profile_matches(profile,scene):raise RuntimeError('Exact original-action definition required')
    try:
        catalog,executor,component,function,current_context=_read_action_preflight(session,profile)
    except RuntimeQueryError as error:
        if str(error)=='Object identity changed or belongs to another process':
            raise NotReady('action_read_preflight: '+str(error)) from error
        raise
    scope=SessionScope(session)
    phase='load_original_asset'
    try:
        loaded=load_asset(scope,profile['action_path']);asset=loaded.return_value
        if asset is None or asset.class_name!='BP_GameAction_CinematicWithLightingScenario_C':
            raise RuntimeError('Original cinematic action class changed')
        phase='observe_loaded_asset'
        # Asset retention can assign a serial to a previously serial-zero object.
        # Observe a wholly new closure after retention, keeping every required
        # exact identity; merging into the pre-retention catalog is invalid.
        required=(asset,executor,component,function)
        catalog=capture_selected(session.pid,tuple((o.index,o.serial,o.address) for o in required))
        # The Blueprint function has reflected local/parameter class constraints
        # beyond the four selected objects. Observe those after retention too;
        # never reuse their pre-load catalog rows.
        dependencies=capture_matching(session.pid,names=('GameAction','GameActionInstance'))
        catalog=catalog.with_observations(dependencies)
        for expected in required:
            observed=catalog.by_index.get(expected.index)
            if observed is None or (observed.pid,observed.index,observed.serial,observed.address)!=(expected.pid,expected.index,expected.serial,expected.address):
                raise RuntimeError('Post-retention action observation identity changed')
        if catalog.path_name(asset)!=profile['action_path']:raise RuntimeError('Original action asset identity changed')
    except BaseException as error:
        error.add_note('original_action phase: '+phase)
        scope.close();raise
    planner=None
    try:
        planner=session.invocation_planner(catalog=catalog,selected_results=True)
        call=planner.prepare(executor,function,GameAction=asset)
    except BaseException as error:
        error.add_note('original_action phase: plan_original_dispatch')
        if planner is not None:planner.close()
        scope.close();raise
    result=PreparedScavenger(planner,call,executor,component,current_context)
    result.scope=scope
    return result

class PreparedScavenger:
    def __init__(self,planner,call,executor,component,context):
        self.planner,self.call=planner,call
        self.executor,self.component,self.context=executor,component,context
        self.dispatched=False
    def play(self):
        if self.dispatched:raise RuntimeError('Original game action cannot be retried')
        self.dispatched=True # Unknown outcome must never dispatch again.
        with self.call.invoke():pass
    def close(self):
        self.planner.close()
        if getattr(self,'scope',None):self.scope.close()

def profile_matches(profile,scene):
    return all(scene.get(key)==profile.get(key) for key in ('id','saved_id','sequence')) and scene.get('sha256',scene.get('definition_sha256'))==profile.get('definition_sha256')

def profiles():
    path=Path(__file__).with_name('original_action_maps.json')
    if not path.exists():return {}
    rows=json.loads(path.read_text(encoding='utf8'))['rows'];result={}
    if len(rows)>155:raise ValueError('Original action mapping exceeds reviewed catalog')
    for row in rows:
        if row.get('travel_mapping_admitted') is not True:continue
        if not re.fullmatch(r'/Game/[A-Za-z0-9_/]+',row.get('exact_map','')):raise ValueError('Invalid mapped travel package')
        if row.get('world_path')!=row['exact_map']+'.'+row['exact_map'].rsplit('/',1)[-1]:raise ValueError('Mapped world identity changed')
        result[row['id']]=row
    return result

def available(transport):
    return type(getattr(transport,'original_game_action_protocol',0)) is int and transport.original_game_action_protocol==1

def _prepare_spawn_recovery(session):
    catalog=capture_matching(session.pid,names=('TeleportToSafeLocation',),classes=('WBP_PauseMenu_C',))
    current=controller_context(session)
    catalog=catalog.with_observations(capture_selected(session.pid,(current['controller'][1:],)))
    player=catalog.by_index[current['controller'][1]]
    values=read_values(catalog,player)
    key=_one(key for key in values.types if key[1]=='PauseMenuWidget')
    owner=catalog.by_index[key[0]]
    target,catalog=read_object_reference(catalog,player,owner,'PauseMenuWidget')
    if target is None or target.class_name!='WBP_PauseMenu_C' or target.object_flags&0x30:
        raise NotReady('Current controller has no initialized native Pause menu')
    function=_one(o for o in catalog.objects if o.name=='TeleportToSafeLocation' and o.class_name=='Function' and o.outer_index==target.class_index)
    _,rows=_query(['--describe',str(session.pid),f'{function.index}:{function.serial}:{function.address:x}'])
    info=_one(r for r in rows if r['event']=='function_metadata')
    if info['params_size']!=0:raise RuntimeError('Native recovery signature changed')
    names=sorted({r[k] for r in rows if r['event']=='property_metadata' for k in ('struct_name','property_class_name','enum_name') if k in r})
    if names:catalog=catalog.with_observations(capture_matching(session.pid,names=names))
    planner=session.invocation_planner(catalog=catalog,selected_results=True)
    try:return planner,planner.prepare(target,function)
    except BaseException:
        planner.close();raise

def recover_spawn(session):
    try:
        # One short read-only worker for this preflight, never across travel or
        # engine invocation. This avoids starting a probe for every field read.
        with ReadBatch(session.pid, share=True):
            planner,call=_prepare_spawn_recovery(session)
    except RuntimeQueryError as error:
        if str(error)=='Object identity changed or belongs to another process':
            raise NotReady('spawn_read_preflight: '+str(error)) from error
        raise
    try:
        with call.invoke():pass
    finally:planner.close()

class OriginalActionReplay:
    """Single pending original action; fresh actors are reacquired after travel."""
    def __init__(self,session,scene,profile):
        if not available(session._session._transport) or not profile_matches(profile,scene):raise RuntimeError('Original action mapping/runtime unavailable')
        self.session,self.scene,self.profile=session,scene,profile
        self.state='new';self.error=None;self.prepared=None;self.next_poll=0.;self.deadline=0.;self.seen_active=False;self.recovered=False;self.phase='new'
        self.travel_started=None;self.recovery_elapsed=None
    def start(self):
        if self.state!='new':raise RuntimeError('Original action request already started')
        self.before_transition=controller_context(self.session)
        # Latest user scope makes history informational for these original routes.
        # Preserve a readable slot, but absent history is not a playback gate.
        try:self.slot=read_current_history(self.session)['selected_slot']
        except (RuntimeError,ValueError,KeyError):self.slot=None
        self.deadline=time.monotonic()+120
        self.state='traveling'
        self.travel_started=time.monotonic()
        try:self.session.console.execute('open '+self.profile['exact_map'])
        except BaseException as error:
            self.error=repr(error);self.state='unknown';raise
        return self.status()
    def poll(self):
        if self.state in ('new','ended','failed','unknown') or time.monotonic()<self.next_poll:return self.status()
        self.next_poll=time.monotonic()+(.05 if self.state in ('traveling','recovering') else .5)
        if time.monotonic()>self.deadline:
            self.error='Original cinematic timed out; no further dispatch attempted';self.state='unknown' if self.prepared and self.prepared.dispatched else 'failed';return self.status()
        if self.state in ('traveling','recovering'):
            try:
                self.phase='observe_controller'
                # Keep repeated readiness reads in one short worker. End the
                # batch before recovery, which may invoke engine code/travel.
                with ReadBatch(self.session.pid, share=True):
                    context=controller_context(self.session)
                if context['controller']==self.before_transition['controller']:raise NotReady('Waiting for a new controller after travel')
                if context['world_path']!=self.profile['world_path']:raise NotReady('Waiting for destination world')
                if not self.recovered:
                    self.phase='recover_spawn'
                    try:recover_spawn(self.session)
                    except NotReady:raise
                    except BaseException as error:
                        self.error=self.phase+': '+repr(error);self.state='unknown';return self.status()
                    self.recovered=True;self.state='recovering';self.before_transition=context;self.error=None
                    self.recovery_elapsed=time.monotonic()-self.travel_started
                    logging.getLogger('expedition33.cinematics').info('Native spawn recovery dispatched %.3fs after open (includes map load)',self.recovery_elapsed)
                    return self.status()
                if self.slot is not None:
                    self.phase='observe_optional_slot'
                    try:slot=read_current_history(self.session)['selected_slot']
                    except (RuntimeError,ValueError,KeyError):slot=None
                    if slot is not None and slot!=self.slot:raise RuntimeError('Selected save slot changed')
                self.phase='prepare_original_action'
                prepared=prepare(self.session,self.scene,self.profile)
                try:
                    self.phase='confirm_controller'
                    latest=controller_context(self.session)
                    if latest!=context:raise NotReady('Controller changed during original-action preparation')
                except BaseException:
                    prepared.close();raise
            except NotReady as error:
                self.error=self.phase+': '+str(error);return self.status()
            except BaseException as error:
                self.error=self.phase+': '+repr(error)+'; '+'; '.join(getattr(error,'__notes__',()));self.state='failed';return self.status()
            self.prepared=prepared;self.state='starting';self.deadline=time.monotonic()+900;self.error=None
            self.phase='dispatch_original_action'
            try:prepared.play()
            except BaseException as error:self.error=self.phase+': '+repr(error);self.state='unknown'
            return self.status()
        try:
            active=_field(_values(self.prepared.executor),'GameActionInstancesInExecution')
            current=_values(self.prepared.component)
            idle=(active=={'$array':{'length':0,'items':[]}} and _field(current,'LevelSequencePlayer') is None and _field(current,'LoadCinematicAssetRequest') is None)
            if not idle:self.seen_active=True;self.state='playing';self.error=None
            elif self.seen_active:self.prepared.close();self.state='ended';self.error=None
        except BaseException as error:self.error=repr(error);self.state='unknown'
        return self.status()
    def status(self):return dict(state=self.state,active=self.state not in ('new','ended','failed'),error=self.error,phase=self.phase,scene=self.profile['id'],map=self.profile['exact_map'],stop_available=False)
