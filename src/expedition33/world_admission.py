"""Read-only save/world admission observations; never retires engine owners."""
from dataclasses import dataclass
import threading
from types import SimpleNamespace

from . import RuntimeQueryError
from ._reader import ReadBatch
from .catalog import capture_matching, capture_selected
from .values import read_object_reference, read_values_many, read_values_with_references, StoredArray, capture_selected_values
from .cinematics.history import anchor, identity, field
from .cinematics.original_game_action import controller_context, NotReady


EXPLORATION_PAWNS = frozenset(('BP_jRPG_Character_WorldMap_pawn_C',
    'BP_jRPG_Character_World_C', 'BP_WorldMapCharacter_C'))


@dataclass(frozen=True)
class Admission:
    state: str
    reason: str
    token: tuple | None = None
    exploration: bool = False

    @property
    def activation_ready(self):
        return self.state == 'world_ready' and self.exploration


def _observe(pid, provider=None):
    catalog = (capture_matching(pid, classes=('GameEngine',)) if provider is None
               else provider.engine_catalog())
    if catalog.pid != pid:
        raise RuntimeError('World admission catalog process mismatch')
    chain, catalog = anchor(catalog, project=True)
    world, gi = chain[2:]
    if provider is not None:provider._ui_anchor=tuple(map(identity,chain))
    gi_owner = catalog.by_index[gi.class_index]
    manager, catalog = read_object_reference(catalog, gi, gi_owner, 'SaveManager', project=True)
    if manager is None:
        return Admission('inactive', 'save_manager_unavailable'), tuple(map(identity, chain)), None
    if manager.class_name != 'BP_SaveManager_C' or manager.object_flags & 0x30:
        raise RuntimeError('World admission save manager class or lifetime mismatch')
    reciprocal, catalog = read_object_reference(catalog, manager,
        catalog.by_index[manager.class_index], 'GameInstanceReference', project=True)
    if reciprocal is None or identity(reciprocal) != identity(gi):
        return Admission('observation_pending', 'save_manager_changed'), None, None
    manager_values = read_values_many(catalog, (manager,),
        fields=('LoadIsInProgress', 'SelectedSlot'))[manager.index]
    gi_values = read_values_many(catalog, (gi,), fields=('SaveLoaded',))[gi.index]
    loading = field(manager_values, 'LoadIsInProgress', 'BoolProperty')
    loaded = field(gi_values, 'SaveLoaded', 'BoolProperty')
    if type(loading) is not bool or type(loaded) is not bool:
        raise RuntimeError('World admission save flags are not strict booleans')
    if loading:
        return Admission('loading', 'save_load_in_progress'), tuple(map(identity, chain)), None
    if not loaded:
        return Admission('inactive', 'save_not_loaded'), tuple(map(identity, chain)), None
    slot = field(manager_values, 'SelectedSlot', 'IntProperty')
    if type(slot) is not int or slot < 0:
        raise RuntimeError('World admission selected slot is invalid')
    current = (controller_context(SimpleNamespace(pid=pid), project=True) if provider is None
               else provider.controller(catalog, gi))
    if tuple(current['world']) != identity(world):
        return Admission('observation_pending', 'controller_world_changed'), None, None
    controller_catalog = capture_selected(pid, (current['controller'][1:],))
    controller = controller_catalog.by_index[current['controller'][1]]
    values = read_values_many(controller_catalog, (controller,), fields=('Pawn',))[controller.index]
    owners = [key[0] for key in values.types if key[1] == 'Pawn']
    if len(owners) != 1:
        raise RuntimeError('World admission controller Pawn field is ambiguous or missing')
    pawn, _ = read_object_reference(controller_catalog, controller,
        controller_catalog.by_index[owners[0]], 'Pawn', project=True)
    if provider is not None:provider._ui_pawn=None if pawn is None else identity(pawn)
    exploration = pawn is not None and pawn.class_name in EXPLORATION_PAWNS
    token = (identity(world), identity(gi), identity(manager), slot)
    return Admission('world_ready', 'exploration_ready' if exploration else 'possession_pending',
                     token, exploration), tuple(map(identity, chain)), tuple(current['controller'])


def observe_admission(pid):
    """Double-observe fresh state; callers must recheck before each activation.

    ``loading``/``inactive`` explicitly inhibit admission. ``observation_pending``
    indicates uncertainty, not teardown. A loaded combat world can retain its
    token with exploration=False: losing an exploration pawn never closes an
    encounter. Every state is read-only; native gates remain authoritative.
    """
    return _read_admission(pid)


def _read_admission(pid, provider=None):
    try:
        with ReadBatch(pid):
            first, first_chain, first_controller = (_observe(pid) if provider is None
                else _observe(pid, provider))
            second, second_chain, second_controller = (_observe(pid) if provider is None
                else _observe(pid, provider))
            if (first, first_chain, first_controller) != (second, second_chain, second_controller):
                return Admission('observation_pending', 'context_changed')
            return second
    except NotReady:
        return Admission('observation_pending', 'controller_unavailable')
    except RuntimeQueryError as error:
        # Only known transport/identity races are transient. Decoder/schema
        # errors remain exceptions, never silently classified as a new world.
        if any(value in str(error) for value in ('READ_FAILED',
                'Object identity changed or belongs to another process',
                'Object property reference changed during observation')):
            return Admission('observation_pending', 'read_unavailable')
        raise
    except RuntimeError as error:
        if str(error) in ('Current history context reference is null',
                'Current history context is ambiguous or unavailable',
                'Active world has no verified game instance'):
            return Admission('observation_pending', 'engine_context_unavailable')
        raise


class WarmAdmissionObserver:
    """Keep one read worker and engine selector, never cached world observations.

    Only the initial engine discovery enumerates the registry. Current local
    player membership is read from each fresh anchored GI.LocalPlayers array.
    Failed workers/selectors are discarded between calls without same-call retry.
    """
    def __init__(self, pid):
        self.pid = pid
        self._owner = threading.get_ident()
        self._reader = None
        self._engine = None
        self._closed = False
        self._activation_binding=None

    def _check(self):
        if self._owner != threading.get_ident():
            raise RuntimeError('Admission observer requires its owner thread')
        if self._closed:
            raise RuntimeError('Admission observer is closed')

    def prepare(self):
        """Start the read-only worker during loading; capture no world data."""
        self._check()
        if self._reader is None:self._reader=ReadBatch(self.pid,share=True)
        with self._reader.bind():pass

    def engine_catalog(self):
        self._check()
        if self._engine is None:
            catalog = capture_matching(self.pid, classes=('GameEngine',))
            engines = tuple(o for o in catalog.select('GameEngine') if not o.object_flags & 0x30)
            if len(engines) != 1:
                raise NotReady('Current engine is unavailable or ambiguous')
            self._engine = identity(engines[0])[1:]
        # Even first discovery is refreshed through exact serial/address selection.
        return capture_selected(self.pid, (self._engine,))

    def controller(self, catalog, gi):
        self._check()
        observed, catalog = read_values_with_references(catalog, gi, fields=('LocalPlayers',))
        players = field(observed, 'LocalPlayers', 'ArrayProperty')
        if not isinstance(players, StoredArray) or players.length != len(players.items):
            raise RuntimeError('Current LocalPlayers array is incomplete')
        if players.length != 1:
            raise NotReady('Current LocalPlayers array is empty or ambiguous')
        local = players.items[0]
        if local is None or local.class_name != 'LocalPlayer' or local.object_flags & 0x30:
            raise RuntimeError('Current LocalPlayers member has an invalid class or lifetime')
        self._ui_local_player=identity(local)
        # The decoder validated the array reference identity and closure. Read the
        # selected member's controller anew; never reuse an earlier membership.
        values = read_values_many(catalog, (local,), fields=('PlayerController',))[local.index]
        owners = [key[0] for key in values.types if key[1] == 'PlayerController']
        if len(owners) != 1:
            raise RuntimeError('Current LocalPlayer controller field is ambiguous or missing')
        player, catalog = read_object_reference(catalog, local,
            catalog.by_index[owners[0]], 'PlayerController', project=True)
        if player is None:
            raise NotReady('Current local controller is unavailable')
        worlds = tuple(o for o in catalog.outer_chain(player) if o.class_name == 'World')
        if len(worlds) != 1:
            raise NotReady('Current local controller world is unavailable or ambiguous')
        self._ui_controller=identity(player)
        return dict(controller=self._ui_controller, world=identity(worlds[0]))

    def _discard(self):
        reader, self._reader = self._reader, None
        self._engine = None
        self._activation_binding=None
        if reader is not None:
            reader.close()

    def observe(self):
        self._check()
        if self._reader is None:
            self._reader = ReadBatch(self.pid, share=True)
        try:
            with self._reader.bind():
                result=_read_admission(self.pid, self)
                self._activation_binding=None
                chain=getattr(self,'_ui_anchor',None)
                local=getattr(self,'_ui_local_player',None)
                controller=getattr(self,'_ui_controller',None)
                pawn=getattr(self,'_ui_pawn',None)
                if (result.activation_ready and chain is not None and len(chain)==4
                        and type(result.token) is tuple and len(result.token)==4
                        and local is not None and controller is not None and pawn is not None):
                    binding=(*chain,result.token[2],tuple(local),tuple(controller),tuple(pawn))
                    if (all(type(row) is tuple and len(row)==4 for row in binding)
                            and binding[2:4]==result.token[:2]):
                        self._activation_binding=binding
                return result
        except BaseException:
            self._discard()
            raise
        finally:
            if self._reader is not None and self._reader._closed:
                self._discard()

    def observe_activation(self):
        """Two fresh class/value passes for a previously fully admitted binding.

        Only selectors are retained. Any changed selector/link withholds this
        operation; the next scheduled call rediscovers through ordinary observe.
        """
        self._check()
        binding=getattr(self,'_activation_binding',None)
        if binding is None:return self.observe()
        if self._reader is None:self._reader=ReadBatch(self.pid,share=True)
        try:
            with self._reader.bind():
                first=self._activation_pass(binding)
                if first.state=='observation_pending':
                    self._activation_binding=None;return first
                second=self._activation_pass(binding)
                if first!=second:
                    self._activation_binding=None
                    return Admission('observation_pending','activation_context_changed')
                if not second.activation_ready:self._activation_binding=None
                return second
        except BaseException:
            self._discard()
            raise

    def confirms_loading_world(self,world,gi):
        """Fresh double root-link check for retirement only, never activation."""
        self._check()
        if self._reader is None:self._reader=ReadBatch(self.pid,share=True)
        try:
            with self._reader.bind():
                def current():
                    chain,_=anchor(self.engine_catalog(),project=True)
                    return tuple(identity(obj) for obj in chain[2:])
                return current()==(world,gi) and current()==(world,gi)
        except (NotReady,RuntimeQueryError):
            self._discard();return False

    def seed_activation(self,binding):
        """Copy read-worker selectors only; both activation passes remain fresh."""
        self._check()
        if (type(binding) is not tuple or len(binding)!=8 or any(
                type(row) is not tuple or len(row)!=4 or
                any(type(value) is not int for value in row) or
                row[0]!=self.pid or row[1]<0 or row[2]<0 or row[3]<=0
                for row in binding)):
            raise ValueError('Expected eight copied activation identities from this process')
        self._activation_binding=binding

    def _activation_pass(self,binding):
        fields=('GameViewport','World','OwningGameInstance','SaveManager','LocalPlayers',
            'SaveLoaded','GameInstanceReference','LoadIsInProgress','SelectedSlot','PlayerController','Player','Pawn')
        catalog,observed=capture_selected_values(self.pid,tuple(row[1:] for row in binding),fields=fields)
        objects=tuple(catalog.by_index[row[1]] for row in binding)
        if tuple(identity(obj) for obj in objects)!=binding:
            return Admission('observation_pending','activation_identity_changed')
        if any(obj.object_flags&0x30 for obj in objects):
            return Admission('observation_pending','activation_lifetime_changed')
        engine,viewport,world,gi,manager,local,pc,pawn=objects
        for obj,kind in ((engine,'GameEngine'),(viewport,'GameViewportClient'),(world,'World'),
                (gi,'BP_jRPG_GI_Custom_C'),(manager,'BP_SaveManager_C'),(local,'LocalPlayer'),(pc,'PlayerController')):
            if catalog.find_class(kind).index not in catalog.ancestors(obj.class_index):
                raise RuntimeQueryError('Activation selected class provenance mismatch')
        def value(obj,name,kind):
            row=observed[obj.index]
            keys=[key for key in row.types if key[1]==name]
            if len(keys)!=1:raise RuntimeQueryError('Activation projection field missing or ambiguous: '+name)
            key=keys[0]
            if key[0] not in catalog.ancestors(obj.class_index) or row.types[key]!=kind:
                raise RuntimeQueryError('Activation projection field provenance mismatch: '+name)
            if key in row.errors or key in row.truncated or key not in row.values:
                return False,None
            return True,row.values[key]
        def link(obj,name,target):
            complete,found=value(obj,name,'ObjectProperty')
            return complete and found is not None and identity(found)==identity(target)
        links=((engine,'GameViewport',viewport),(viewport,'World',world),(world,'OwningGameInstance',gi),
            (gi,'SaveManager',manager),(manager,'GameInstanceReference',gi),
            (local,'PlayerController',pc),(pc,'Player',local),(pc,'Pawn',pawn))
        if not all(link(*args) for args in links):
            return Admission('observation_pending','activation_reference_changed')
        complete,players=value(gi,'LocalPlayers','ArrayProperty')
        if (not complete or not isinstance(players,StoredArray) or players.length!=1 or len(players.items)!=1
                or players.items[0] is None or identity(players.items[0])!=identity(local)):
            return Admission('observation_pending','activation_membership_changed')
        worlds=tuple(obj for obj in catalog.outer_chain(pc) if obj.class_name=='World')
        if len(worlds)!=1 or identity(worlds[0])!=identity(world):
            return Admission('observation_pending','activation_controller_world_changed')
        pawn_worlds=tuple(obj for obj in catalog.outer_chain(pawn) if obj.class_name=='World')
        if len(pawn_worlds)!=1 or identity(pawn_worlds[0])!=identity(world):
            return Admission('observation_pending','activation_pawn_world_changed')
        flags=[]
        for obj,name,kind in ((gi,'SaveLoaded','BoolProperty'),(manager,'LoadIsInProgress','BoolProperty'),(manager,'SelectedSlot','IntProperty')):
            complete,found=value(obj,name,kind)
            if not complete:return Admission('observation_pending','activation_flags_incomplete')
            flags.append(found)
        loaded,loading,slot=flags
        if type(loaded) is not bool or type(loading) is not bool:
            raise RuntimeQueryError('Activation projection save flags invalid')
        if loading:return Admission('loading','save_load_in_progress')
        if not loaded:return Admission('inactive','save_not_loaded')
        if type(slot) is not int or slot<0:raise RuntimeQueryError('Activation projection selected slot invalid')
        token=(identity(world),identity(gi),identity(manager),slot)
        exploration=pawn.class_name in EXPLORATION_PAWNS
        return Admission('world_ready','exploration_ready' if exploration else 'possession_pending',token,exploration)

    def close(self):
        if self._owner != threading.get_ident():
            raise RuntimeError('Admission observer requires its owner thread')
        if not self._closed:
            self._discard()
            self._closed = True
