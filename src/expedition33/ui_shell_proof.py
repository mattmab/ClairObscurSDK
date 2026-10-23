"""Explicit handoff proof for the SDK's exact owned ScrollWorkspacePanel tree.

Prototype only. Runs on the Session owner at a context boundary, never a passive
poll. Uses existing typed APIs and their native schema/identity gates. No raw
memory reads/writes, guessed offsets, global callback enable or scope reparenting.
"""
from dataclasses import dataclass
from . import RuntimeQueryError
from ._reader import ReadBatch
from .catalog import capture_matching,capture_selected
from .values import read_object_reference,read_values_many,read_values_with_references,StoredArray
from .cinematics.history import anchor,field,identity
from .world_admission import EXPLORATION_PAWNS

TITLE_WORLD='/Game/Levels/UI/MainMenu/Level_MainMenu.Level_MainMenu'


class UiProofPending(RuntimeError):pass
class UiProofMismatch(RuntimeError):pass
class UiProofPreflightRejected(UiProofMismatch):
    """Pure tree-read/size rejection; retain frontend owners without replay."""


SELECTED_CHUNK=1024
MAX_SELECTED_OBJECTS=8192
PROOF_CONSTRAINT_CLASSES=('/Script/Engine.LocalPlayer','/Script/Engine.PlayerController',
    '/Script/UMG.Widget','/Script/UMG.UserWidget')


def capture_complete(pid,selectors):
    """Fresh complete selected reads; the native request bound is unchanged."""
    selectors=tuple(dict.fromkeys(selectors))
    if not selectors or len(selectors)>MAX_SELECTED_OBJECTS:
        raise UiProofPreflightRejected('Reusable UI graph exceeds bounded ownership capacity')
    fresh=None
    for offset in range(0,len(selectors),SELECTED_CHUNK):
        # Each native read verifies its dependency closure; Catalog checks all
        # shared identity/class relations. No uncovered object is discarded.
        try:
            observed=capture_selected(pid,selectors[offset:offset+SELECTED_CHUNK])
            fresh=observed if fresh is None else fresh.with_observations(observed)
        except RuntimeQueryError as error:
            if any(reason in str(error) for reason in ('Object identity changed or belongs to another process',
                    'Planning class relation changed; full refresh required','READ_FAILED',
                    'DESCRIPTOR_IDENTITY_CHANGED','SELECTED_DEPENDENCY_CHANGED')):
                raise UiProofPending('Selected UI closure changed between proof chunks') from None
            raise
    for index,serial,address in selectors:
        obj=fresh.by_index.get(index)
        if obj is None or (obj.pid,obj.serial,obj.address)!=(pid,serial,address):
            raise UiProofPending('Selected UI proof returned an incomplete or changed identity')
    return fresh


def graph_signature(obj):
    return (obj.pid,obj.index,obj.serial,obj.address,obj.name,obj.class_index,
        obj.outer_index,obj.outer_serial,obj.object_flags)


@dataclass(frozen=True)
class UiContext:
    kind: str
    world: tuple
    gi: tuple
    local_player: tuple
    controller: tuple

    def __post_init__(self):
        if self.kind not in ('title','world'):raise ValueError('Expected title or world UI context')
        values=(self.world,self.gi,self.local_player,self.controller)
        if any(type(v) is not tuple or len(v)!=4 or any(type(n) is not int for n in v) for v in values):
            raise ValueError('UI context requires copied process/index/serial/address identities')
        if len({v[0] for v in values})!=1:raise ValueError('UI context process mismatch')

    @property
    def signature(self):return self.kind,self.world,self.gi,self.local_player,self.controller
    @property
    def persistent_key(self):return self.gi,self.local_player


class OwnedUiProof:
    def __init__(self,scope):
        self.scope=scope;self._engine=None;self.pending_results=[];self._setter_done=None

    def pending(self):
        self.pending_results[:]=[r for r in self.pending_results
            if any(getattr(lease,'_state',None)!='released' for lease in r._leases)]
        return bool(self.pending_results)

    def _current(self,context):
        if self.pending():raise UiProofPending('UI getter leases cleanup pending; retain proof owner')
        pid=self.scope.pid
        if self._engine is None:
            catalog=capture_matching(pid,classes=('GameEngine',))
            rows=[o for o in catalog.select('GameEngine') if not o.object_flags&0x30]
            if len(rows)!=1:raise UiProofPending('Current UI engine unavailable')
            self._engine=identity(rows[0])[1:]
        catalog=capture_selected(pid,(self._engine,))
        chain,catalog=anchor(catalog,project=True);world,gi=chain[2:]
        if (identity(world),identity(gi))!=(context.world,context.gi):
            raise UiProofPending('UI world or game instance changed before handoff')
        observed,catalog=read_values_with_references(catalog,gi,fields=('LocalPlayers',))
        players=field(observed,'LocalPlayers','ArrayProperty')
        if not isinstance(players,StoredArray) or players.length!=1 or len(players.items)!=1:
            raise UiProofPending('UI requires one complete current LocalPlayer')
        local=players.items[0]
        if local is None or local.class_name!='LocalPlayer' or identity(local)!=context.local_player:
            raise UiProofPending('Current UI LocalPlayer changed')
        def reference(obj,owner,name):
            nonlocal catalog
            value,catalog=read_object_reference(catalog,obj,catalog.by_index[catalog.find_class(owner).index],name,project=True)
            return value
        pc=reference(local,'Player','PlayerController')
        if pc is None or identity(pc)!=context.controller:raise UiProofPending('Current UI controller changed')
        if reference(pc,'PlayerController','Player')!=local:raise UiProofMismatch('UI controller backlink mismatch')
        worlds=[o for o in catalog.outer_chain(pc) if o.class_name=='World']
        if len(worlds)!=1 or identity(worlds[0])!=context.world:raise UiProofMismatch('UI controller belongs to another world')
        if context.kind=='title':
            if catalog.path_name(world)!=TITLE_WORLD or pc.class_name!='BP_jRPG_Controller_MainMenu_C':
                raise UiProofPending('Current title UI context unavailable')
        else:
            flags=read_values_many(catalog,(gi,),fields=('SaveLoaded','IsChangingMap'))[gi.index]
            if field(flags,'SaveLoaded','BoolProperty') is not True or field(flags,'IsChangingMap','BoolProperty') is not False:
                raise UiProofPending('Gameplay UI save context is loading')
            # SaveManager is game-owned, not an Engine.GameInstance field.
            owner=catalog.by_index[gi.class_index]
            manager,catalog=read_object_reference(catalog,gi,owner,'SaveManager',project=True)
            if manager is None:raise UiProofPending('Gameplay save manager unavailable')
            reciprocal,catalog=read_object_reference(catalog,manager,catalog.by_index[manager.class_index],
                'GameInstanceReference',project=True)
            loading=read_values_many(catalog,(manager,),fields=('LoadIsInProgress',))[manager.index]
            if reciprocal!=gi or field(loading,'LoadIsInProgress','BoolProperty') is not False:
                raise UiProofPending('Gameplay save manager changed or loading')
            pawn=reference(pc,'Controller','Pawn')
            if pawn is None or pawn.class_name not in EXPLORATION_PAWNS:
                raise UiProofPending('First gameplay UI handoff awaits exploration')
        return catalog,pc

    def _graph(self,panel,context,catalog):
        from .mods_workspace_scroll import ScrollWorkspacePanel
        if type(panel) is not ScrollWorkspacePanel:raise UiProofPreflightRejected('Only exact SDK ScrollWorkspacePanel can be reused')
        if panel.state!='built' or panel.menu is not None or panel.uncertain:
            raise UiProofPending('Native UI close ACK required before tree proof')
        objects=[lease.object for lease in panel.scope._leases if lease.active]
        objects.extend((panel.widget,panel.tree,panel.canvas))
        selectors=tuple(dict.fromkeys(identity(obj)[1:] for obj in objects))
        first=capture_complete(self.scope.pid,selectors)
        before={index:graph_signature(first.by_index[index]) for index,_serial,_address in selectors}
        # Repeat every selected object's proof, including those in earlier
        # chunks. A merged catalog alone cannot establish fresh outer topology.
        current=capture_complete(self.scope.pid,tuple(reversed(selectors)))
        if any(before[index]!=graph_signature(current.by_index[index])
                for index,_serial,_address in selectors):
            raise UiProofPending('Owned UI graph changed during complete proof')
        root=current.resolve(panel.widget);tree=current.resolve(panel.tree)
        if root.class_name!='CommonActivatableWidget' or root.object_flags&0x40000030:
            raise UiProofPreflightRejected('Reusable root has unsupported class or lifetime')
        if (root.outer_index,root.outer_serial)!=(context.gi[1],context.gi[2]):
            raise UiProofPreflightRejected('Reusable root is not directly owned by the current game instance')
        if tree.class_name!='WidgetTree' or (tree.outer_index,tree.outer_serial)!=(root.index,root.serial):
            raise UiProofPreflightRejected('Reusable WidgetTree ownership mismatch')
        user_class=current.find_class('UserWidget').index
        for obj in objects:
            fresh=current.resolve(obj)
            if fresh.object_flags&0x40000030:raise UiProofPreflightRejected('Owned UI object lifetime changed')
            if fresh.index!=root.index and user_class in current.ancestors(fresh.class_index):
                raise UiProofPreflightRejected('Nested UserWidgets require an independent context proof')
            if fresh.index!=root.index and root.index not in {o.index for o in current.outer_chain(fresh)}:
                raise UiProofPreflightRejected('Owned UI object escaped the root tree')
        root_tree,current=read_object_reference(current,root,current.by_index[user_class],'WidgetTree',project=True)
        assigned,current=read_object_reference(current,tree,current.by_index[tree.class_index],'RootWidget',project=True)
        if root_tree!=tree or assigned!=current.resolve(panel.canvas):raise UiProofPreflightRejected('Owned root property readback mismatch')
        return catalog.with_observations(current)

    def _functions(self,catalog):
        from ._metadata_stabilization import available,prepare_discovery
        from ._stable_lease import fresh_catalog_replacing
        def discover():
            return capture_matching(self.scope.pid,names=('SetOwningPlayer','GetOwningPlayer','GetOwningLocalPlayer',
                'GetPlayerController','Default__GameplayStatics','Default__LocalPlayer',
                'Default__PlayerController','Default__Widget','Default__UserWidget'))
        if not available(self.scope._session._transport):
            raise UiProofMismatch('Process UI proof requires positive metadata preparation')
        extra,_=prepare_discovery(self.scope._session,discover)
        # Function object closure does not include every FObjectProperty's
        # constraint. These exact native getter outputs/setter input classes
        # are discovered through their CDOs and the same Script provenance gate.
        for path in PROOF_CONSTRAINT_CLASSES:
            if extra.find_path(path,'Class').serial<=0:
                raise UiProofPreflightRejected('UI proof constraint metadata was not stabilized')
        # Metadata stabilization may assign a serial to a previously zero row.
        # Never merge that transition into the pre-boundary planning catalog.
        return fresh_catalog_replacing(catalog,extra.objects)

    def _invoke(self,catalog,target,owner,name,**args):
        cls=catalog.find_class(owner).index
        matches=[o for o in catalog.objects if o.class_name=='Function' and o.outer_index==cls and o.name==name]
        if len(matches)!=1:raise UiProofMismatch('UI proof function unavailable or ambiguous')
        planner=self.scope.invocation_planner(catalog=catalog,selected_results=True)
        planner._require_stable_ui_identities=True
        try:
            result=planner.prepare(target,matches[0],**args).invoke()
            self.pending_results.append(result) # retain before exposing any result
            value=result.return_value
            if not result.release():raise UiProofPending('UI getter leases cleanup pending; retain proof owner')
            self.pending_results.remove(result)
            return value
        finally:planner.close()

    def verify(self,panel,context,*,rebind=False):
        with ReadBatch(self.scope.pid):
            catalog,pc=self._current(context)
            catalog=self._functions(self._graph(panel,context,catalog))
            root=catalog.resolve(panel.widget)
            if rebind and self._setter_done!=context.signature:
                # Reserve this single dispatch before invoking. A pending
                # result-release ACK must never replay an already returned
                # setter; unknown dispatch errors quarantine the router.
                self._setter_done=context.signature
                self._invoke(catalog,root,'UserWidget','SetOwningPlayer',LocalPlayerController=pc)
            owning=self._invoke(catalog,root,'Widget','GetOwningPlayer')
            local=self._invoke(catalog,root,'Widget','GetOwningLocalPlayer')
            libraries=[o for o in catalog.select('GameplayStatics') if o.name=='Default__GameplayStatics']
            if len(libraries)!=1:raise UiProofMismatch('UI proof library unavailable')
            # The shipping getter calls root.GetWorld, and checks returnedWorld
            # against GI's current world BEFORE using GI.LocalPlayers. Otherwise
            # it enumerates controllers from that returned world's actor list.
            world_pc=self._invoke(catalog,libraries[0],'GameplayStatics','GetPlayerController',
                WorldContextObject=root,PlayerIndex=0)
            if (owning is None or local is None or world_pc is None or
                    identity(owning)!=context.controller or identity(local)!=context.local_player or
                    identity(world_pc)!=context.controller):
                raise UiProofMismatch('Typed widget owning-player/local-player/world readback mismatch')
            self._current(context) # reject a generation switch during getter calls
            if rebind:
                # Old controller/world copies are discarded. The native menu
                # prepare cache already keys PC identity; explicitly revoke it.
                self.scope._session._menu_plan_cache=None
                panel.player=pc
                panel._planner.close()
                # Root, children, current context and unchanged metadata are
                # selected anew; no old PC/world catalog is merged here.
                metadata=[o for o in panel.catalog.objects if o.class_name in ('Function','Class','ScriptStruct','Enum')
                    or o.name in ('Default__GameplayStatics','Default__WidgetBlueprintLibrary')]
                objects=[lease.object for lease in panel.scope._leases if lease.active]
                selectors=tuple(dict.fromkeys(identity(o)[1:] for o in (*metadata,*objects,pc)))
                fresh=capture_complete(self.scope.pid,selectors)
                panel.catalog=fresh
                panel._planner=panel.scope.invocation_planner(catalog=fresh,selected_results=True)
                panel._planner._require_stable_ui_identities=getattr(panel,'_metadata_stable_ui',False)
                panel.prime_menu_plan()
            return True
