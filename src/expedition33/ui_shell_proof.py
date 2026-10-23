"""Explicit handoff proof for an exactly registered detached UMG panel type.

Runs on the Session owner at a context boundary, never a passive
poll. Uses existing typed APIs and their native schema/identity gates. No raw
memory reads/writes, guessed offsets, global callback enable or scope reparenting.
"""
from dataclasses import dataclass
from . import RuntimeQueryError
from ._reader import ReadBatch
from .catalog import capture_matching,capture_selected
from .values import read_object_reference,read_values_many,read_values_with_references,StoredArray,capture_selected_values
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


def prepare_panel_metadata(panel):
    """Finish retained Script metadata admission during detached construction.

    Unrelated game/Blueprint metadata is not admitted. Each changed identity is
    recaptured before replacing planners; this grants no gameplay authority.
    """
    from ._metadata_stabilization import script_function,process_preparation,CAPACITY
    from ._stable_lease import fresh_catalog_replacing
    # Construction adopts owned outputs into the planner's catalog. The
    # panel's initial discovery catalog can still omit the generated widgets.
    catalog=panel._planner._catalog
    retained=[];candidates=[]
    for obj in catalog.objects:
        try:script_function(catalog,obj)
        except ValueError:continue
        retained.append(obj)
        if not obj.serial:candidates.append(obj)
    if not candidates:return
    # Broad name discovery can include unrelated game Blueprint functions.
    # They are neither UI dependencies nor ours to keep across loading. Keep
    # the retained native metadata plus the complete leased tree/current PC.
    retained.extend(lease.object for lease in panel.scope._leases if lease.active)
    # Read-only POD/enum descriptors can live outside the stabilization
    # whitelist (for example /Script/Slate.Anchors). They are still required
    # to validate typed setters. Retain their exact observations without
    # granting metadata leases or admitting unrelated Blueprint functions.
    retained.extend(o for o in catalog.objects if o.class_name in ('ScriptStruct','Enum'))
    retained.extend((panel.widget,panel.tree,panel.canvas,panel.player))
    retained.extend(o for o in catalog.objects if o.class_name=='GameEngine' and not o.object_flags&0x30)
    catalog=catalog.subset(retained)
    session=panel.scope._session;owner=process_preparation(session);replacements={}
    for offset in range(0,len(candidates),CAPACITY):
        observed=owner.prepare(catalog,candidates[offset:offset+CAPACITY])
        replacements.update(observed.by_index)
    fresh=fresh_catalog_replacing(catalog,tuple(replacements.values()))
    panel._planner.close();panel.catalog=fresh
    panel._functions.clear();panel._defaults.clear()
    panel._planner=panel.scope.invocation_planner(catalog=fresh,selected_results=True)
    panel._planner._require_stable_ui_identities=getattr(panel,'_metadata_stable_ui',False)
    session._menu_plan_cache=None
    schemas=getattr(session,'_menu_schema_observations',None)
    if schemas is not None:schemas.clear()


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
                raise UiProofPending('Selected UI closure changed between proof chunks '
                    f'(offset {offset}): {str(error)[-512:]}') from None
            raise
    for index,serial,address in selectors:
        obj=fresh.by_index.get(index)
        if obj is None or (obj.pid,obj.serial,obj.address)!=(pid,serial,address):
            raise UiProofPending('Selected UI proof returned an incomplete or changed identity')
    return fresh


def graph_signature(obj):
    return (obj.pid,obj.index,obj.serial,obj.address,obj.name,obj.class_index,
        obj.outer_index,obj.outer_serial,obj.object_flags)


def same_identity(observed,expected):
    # UObject flags are observations, not identity. GC may change them between
    # two valid reference reads without changing the referenced object.
    return observed is not None and expected is not None and identity(observed)==identity(expected)


def refresh_panel_metadata(pid,previous,*,observed=None):
    """Rediscover descriptors after admitted metadata gained positive serials.

    A serial-zero descriptor is never reused as an exact selector. Positive
    identities must still match, and zero transitions must preserve address,
    index, name and class. This refresh applies only to planner metadata.
    """
    # A CDO's dependency closure includes its class. Bare class names can also
    # match thousands of blueprint components; CDO names keep discovery bounded.
    rows=[]
    for old in previous:
        current=(observed.by_index.get(old.index,old) if observed is not None and
            old.class_name=='Class' and old.serial==0 else old)
        if (current.pid,current.index,current.address,current.name,current.class_index)!=(
                old.pid,old.index,old.address,old.name,old.class_index):
            raise UiProofPending('Panel metadata identity changed during selected refresh')
        rows.append(current)
    previous=tuple(rows)
    names=tuple(sorted({'Default__'+o.name for o in previous if o.class_name=='Class' and o.serial==0
        and (observed is None or o.index not in observed.by_index)}))
    if not names:return tuple(previous)
    fresh=None
    for offset in range(0,len(names),128):
        group=names[offset:offset+128]
        try:observed=capture_matching(pid,names=group)
        except RuntimeQueryError as error:
            raise UiProofPending('Panel metadata rediscovery is temporarily unavailable: '
                +str(error)[-200:]+': '+repr(group)) from None
        fresh=observed if fresh is None else fresh.with_observations(observed)
    rows=[]
    for old in previous:
        # Class descriptors can acquire serials while typed metadata is admitted.
        # Functions/default objects retain their exact selectors and are read
        # afresh by capture_complete below; matching generic function names
        # would enumerate unrelated game objects with those names.
        current=fresh.by_index.get(old.index,old) if old.class_name=='Class' and old.serial==0 else old
        if (current is None or current.pid!=old.pid or current.address!=old.address
                or current.name!=old.name or current.class_index!=old.class_index
                or (old.serial>0 and current.serial!=old.serial)):
            raise UiProofPending('Panel metadata identity changed during rediscovery')
        rows.append(current)
    return tuple(rows)


def panel_metadata(catalog):
    """Only UI Script descriptors and copied POD/enum dependencies survive.

    Name discovery can encounter unrelated functions with the same short name.
    Their class closures are not UI planner inputs. Current engine/GI/controller
    classes instead come from the independently fresh context proof.
    """
    from ._metadata_stabilization import script_function
    result=[]
    for obj in catalog.objects:
        if obj.class_name not in ('Function','Class','ScriptStruct','Enum') and obj.name not in (
                'Default__GameplayStatics','Default__WidgetBlueprintLibrary'):continue
        try:script_function(catalog,obj)
        except ValueError:
            if obj.class_name not in ('ScriptStruct','Enum'):continue
        result.append(obj)
    return tuple(result)


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
    def __init__(self,scope,*,panel_type=None,prime=True):
        from .mods_workspace_scroll import ScrollWorkspacePanel
        self.panel_type=panel_type or ScrollWorkspacePanel
        self.prime=prime
        self.scope=scope;self._engine=None;self.pending_results=[];self._setter_done=None

    def pending(self):
        self.pending_results[:]=[r for r in self.pending_results
            if any(getattr(lease,'_state',None)!='released' for lease in r._leases)]
        return bool(self.pending_results)

    def _current(self,context,*,preparing=False):
        try:return self._current_observation(context,preparing=preparing)
        except RuntimeQueryError as error:
            if any(reason in str(error) for reason in ('DESCRIPTOR_IDENTITY_CHANGED','READ_FAILED',
                    'SELECTED_DEPENDENCY_CHANGED','Object identity changed or belongs to another process',
                    'Object property reference changed during observation')):
                raise UiProofPending('UI context changed during loading observation') from None
            raise
        except RuntimeError as error:
            if str(error) in ('Current history context reference is null',
                    'Current history context is ambiguous or unavailable','Active world has no verified game instance'):
                raise UiProofPending('UI world is between loading generations') from None
            raise

    def _current_observation(self,context,*,preparing=False):
        if self.pending():raise UiProofPending('UI getter leases cleanup pending; retain proof owner')
        pid=self.scope.pid
        if context.kind=='world' and getattr(self,'_viewport',None) is not None:
            try:return self._loading_current(context,gameplay=not preparing)
            except (RuntimeQueryError,UiProofPending):
                self._viewport=None
                raise # Next scheduled proof rediscovers; never replay this one.
        if self._engine is None:
            catalog=capture_matching(pid,classes=('GameEngine',))
            rows=[o for o in catalog.select('GameEngine') if not o.object_flags&0x30]
            if len(rows)!=1:raise UiProofPending('Current UI engine unavailable')
            self._engine=identity(rows[0])[1:]
        catalog=capture_selected(pid,(self._engine,))
        chain,catalog=anchor(catalog,project=True);world,gi=chain[2:]
        self._viewport=identity(chain[1])[1:]
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
        if not same_identity(reference(pc,'PlayerController','Player'),local):raise UiProofMismatch('UI controller backlink mismatch')
        worlds=[o for o in catalog.outer_chain(pc) if o.class_name=='World']
        if len(worlds)!=1 or identity(worlds[0])!=context.world:raise UiProofMismatch('UI controller belongs to another world')
        if context.kind=='title':
            if catalog.path_name(world)!=TITLE_WORLD or pc.class_name!='BP_jRPG_Controller_MainMenu_C':
                raise UiProofPending('Current title UI context unavailable')
        elif not preparing:
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
            if not same_identity(reciprocal,gi) or field(loading,'LoadIsInProgress','BoolProperty') is not False:
                raise UiProofPending('Gameplay save manager changed or loading')
            pawn=reference(pc,'Controller','Pawn')
            if pawn is None or pawn.class_name not in EXPLORATION_PAWNS:
                raise UiProofPending('First gameplay UI handoff awaits exploration')
        return catalog,pc

    def _loading_current(self,context,*,gameplay=False):
        """One fresh read of the same detached-loading anchor/player links."""
        fields=('GameViewport','World','OwningGameInstance','LocalPlayers','PlayerController','Player')
        if gameplay:fields+=('SaveLoaded','IsChangingMap','SaveManager','Pawn')
        selectors=(self._engine,self._viewport,context.world[1:],context.gi[1:],
            context.local_player[1:],context.controller[1:])
        catalog,rows=capture_selected_values(self.scope.pid,selectors,fields=fields,references=gameplay)
        engine,viewport,world,gi,local,pc=(catalog.by_index[row[0]] for row in selectors)
        for obj,kind in ((engine,'GameEngine'),(viewport,'GameViewportClient'),(world,'World'),
                (gi,'BP_jRPG_GI_Custom_C'),(local,'LocalPlayer'),(pc,'PlayerController')):
            if obj.object_flags&0x40000030 or catalog.find_class(kind).index not in catalog.ancestors(obj.class_index):
                raise UiProofPending('Loading UI anchor lifetime or class changed')
        def value(obj,name,kind):
            row=rows[obj.index];keys=[key for key in row.types if key[1]==name]
            if len(keys)!=1:raise RuntimeQueryError('Loading UI field missing or ambiguous')
            key=keys[0]
            if key[0] not in catalog.ancestors(obj.class_index) or row.types[key]!=kind:
                raise RuntimeQueryError('Loading UI field provenance changed')
            if key in row.errors or key in row.truncated or key not in row.values:
                raise UiProofPending('Loading UI field unavailable')
            return row.values[key]
        for obj,name,target in ((engine,'GameViewport',viewport),(viewport,'World',world),
                (world,'OwningGameInstance',gi),(local,'PlayerController',pc),(pc,'Player',local)):
            if not same_identity(value(obj,name,'ObjectProperty'),target):
                raise UiProofPending('Loading UI anchor/player link changed')
        players=value(gi,'LocalPlayers','ArrayProperty')
        if (not isinstance(players,StoredArray) or players.length!=1 or len(players.items)!=1
                or not same_identity(players.items[0],local)):
            raise UiProofPending('Loading UI LocalPlayer membership changed')
        worlds=[obj for obj in catalog.outer_chain(pc) if obj.class_name=='World']
        if len(worlds)!=1 or identity(worlds[0])!=context.world:
            raise UiProofPending('Loading UI controller world changed')
        if gameplay:
            if (value(gi,'SaveLoaded','BoolProperty') is not True or
                    value(gi,'IsChangingMap','BoolProperty') is not False):
                raise UiProofPending('Gameplay UI save context is loading')
            pawn=value(pc,'Pawn','ObjectProperty')
            if pawn is None or pawn.class_name not in EXPLORATION_PAWNS:
                raise UiProofPending('First gameplay UI handoff awaits exploration')
            manager=value(gi,'SaveManager','ObjectProperty')
            if manager is None:raise UiProofPending('Gameplay save manager unavailable')
            # The manager is discovered by the first projection. Read its
            # reciprocal/loading fields freshly together with GI's reference;
            # no cached property values cross either boundary proof.
            observed,manager_rows=capture_selected_values(self.scope.pid,
                (identity(gi)[1:],identity(manager)[1:]),
                fields=('SaveManager','GameInstanceReference','LoadIsInProgress'))
            catalog=catalog.with_observations(observed)
            rows=manager_rows
            if (not same_identity(value(gi,'SaveManager','ObjectProperty'),manager) or
                    not same_identity(value(manager,'GameInstanceReference','ObjectProperty'),gi) or
                    value(manager,'LoadIsInProgress','BoolProperty') is not False):
                raise UiProofPending('Gameplay save manager changed or loading')
        return catalog,pc

    def _graph(self,panel,context,catalog):
        from .mods_workspace_scroll import ScrollWorkspacePanel
        if type(panel) is not getattr(self,'panel_type',ScrollWorkspacePanel):raise UiProofPreflightRejected('Panel type differs from the explicitly registered detached tree')
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
        if not same_identity(root_tree,tree) or not same_identity(assigned,current.resolve(panel.canvas)):raise UiProofPreflightRejected('Owned root property readback mismatch')
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
        session=self.scope._session
        selectors=getattr(session,'_ui_proof_metadata_selectors',None)
        if selectors is None:
            extra,_=prepare_discovery(session,discover)
            # Retained Script metadata is process-owned. Subsequent roots and
            # world handoffs need fresh selected reads, not another global scan.
            selectors=tuple(identity(o)[1:] for o in extra.objects if o.serial>0 and
                (o.class_name=='Function' and o.name in ('SetOwningPlayer','GetOwningPlayer',
                    'GetOwningLocalPlayer','GetPlayerController') or
                 o.name in ('Default__GameplayStatics','Default__LocalPlayer',
                    'Default__PlayerController','Default__Widget','Default__UserWidget') or
                 o.class_name=='Class' and extra.path_name(o) in PROOF_CONSTRAINT_CLASSES))
            session._ui_proof_metadata_selectors=selectors
        else:extra=capture_selected(self.scope.pid,selectors)
        # Function object closure does not include every FObjectProperty's
        # constraint. These exact native getter outputs/setter input classes
        # are discovered through their CDOs and the same Script provenance gate.
        for path in PROOF_CONSTRAINT_CLASSES:
            if extra.find_path(path,'Class').serial<=0:
                raise UiProofPreflightRejected('UI proof constraint metadata was not stabilized')
        # Metadata stabilization may assign a serial to a previously zero row.
        # Never merge that transition into the pre-boundary planning catalog.
        # Preparing getter metadata can also admit a previously zero class in
        # the live engine/GI closure. Rediscover those exact class identities
        # before selecting the combined closure; do not reuse their old zeros.
        # Only the first stabilization can change our metadata serials. Later
        # selected reads contain already admitted identities; merging them into
        # the freshly proved graph needs no global CDO scan or tree recapture.
        metadata=(() if getattr(self,'_metadata_warmed',False) else
            refresh_panel_metadata(self.scope.pid,tuple(o for o in catalog.objects
                if o.class_name=='Class' and o.serial==0 and o.index not in extra.by_index)))
        try:
            combined=(catalog.with_observations(extra) if getattr(self,'_metadata_warmed',False)
                else fresh_catalog_replacing(catalog,(*extra.objects,*metadata)))
        except RuntimeQueryError as error:
            if any(reason in str(error) for reason in ('DESCRIPTOR_IDENTITY_CHANGED','READ_FAILED',
                    'SELECTED_DEPENDENCY_CHANGED','Object identity changed or belongs to another process',
                    'Planning class relation changed; full refresh required')):
                self._metadata_warmed=False
                raise UiProofPending('UI metadata changed during loading handoff') from None
            raise

        from ._planning_metadata import MetadataObservations
        from .reflection import describe
        if not hasattr(self,'_getter_metadata'):self._getter_metadata=MetadataObservations()
        getters=tuple(o for o in combined.objects if o.class_name=='Function' and
            o.name in ('SetOwningPlayer','GetOwningPlayer','GetOwningLocalPlayer','GetPlayerController') and
            combined.by_index[o.outer_index].name in ('UserWidget','Widget','GameplayStatics'))
        self._getter_metadata.read('struct',combined,getters,describe)
        self._metadata_warmed=True
        return combined

    def _invoke(self,catalog,target,owner,name,**args):
        cls=catalog.find_class(owner).index
        matches=[o for o in catalog.objects if o.class_name=='Function' and o.outer_index==cls and o.name==name]
        if len(matches)!=1:raise UiProofMismatch('UI proof function unavailable or ambiguous')
        planner=self.scope.invocation_planner(catalog=catalog,selected_results=True)
        metadata=getattr(self,'_getter_metadata',None)
        if metadata is None:
            from ._planning_metadata import MetadataObservations
            metadata=MetadataObservations();self._getter_metadata=metadata
        planner._metadata._entries=dict(metadata._entries)
        planner._require_stable_ui_identities=True
        try:
            prepared=planner.prepare(target,matches[0],**args)
            metadata._entries=dict(planner._metadata._entries)
            result=prepared.invoke()
            self.pending_results.append(result) # retain before exposing any result
            value=result.return_value
            if not result.release():raise UiProofPending('UI getter leases cleanup pending; retain proof owner')
            self.pending_results.remove(result)
            return value
        finally:planner.close()

    def verify(self,panel,context,*,rebind=False,preparing=False):
        try:return self._verify_observation(panel,context,rebind=rebind,preparing=preparing)
        except RuntimeQueryError as error:
            if any(reason in str(error) for reason in ('DESCRIPTOR_IDENTITY_CHANGED','READ_FAILED',
                    'SELECTED_DEPENDENCY_CHANGED','Object identity changed or belongs to another process',
                    'Object property reference changed during observation')):
                raise UiProofPending('UI closure changed during loading handoff') from None
            raise

    def _verify_observation(self,panel,context,*,rebind=False,preparing=False):
        if getattr(self,'_rejected_setter_context',None)==context.signature:
            raise UiProofPending('Rejected loading controller; awaiting a different current UI context')
        with ReadBatch(self.scope.pid):
            current=lambda:self._current(context,preparing=True) if preparing else self._current(context)
            catalog,pc=current()
            catalog=self._functions(self._graph(panel,context,catalog))
            root=catalog.resolve(panel.widget)
            libraries=[o for o in catalog.select('GameplayStatics') if o.name=='Default__GameplayStatics']
            if len(libraries)!=1:raise UiProofMismatch('UI proof library unavailable')
            def readback():
                owning=self._invoke(catalog,root,'Widget','GetOwningPlayer')
                local=self._invoke(catalog,root,'Widget','GetOwningLocalPlayer')
                world_pc=self._invoke(catalog,libraries[0],'GameplayStatics','GetPlayerController',
                    WorldContextObject=root,PlayerIndex=0)
                return (owning is not None and local is not None and world_pc is not None and
                    identity(owning)==context.controller and identity(local)==context.local_player and
                    identity(world_pc)==context.controller)
            # A GI-owned widget's LocalPlayer can already resolve the new
            # controller/world. Prove that through all three shipping getters
            # before issuing an unnecessary ownership mutation during loading.
            matched=readback()
            if not matched and rebind and self._setter_done!=context.signature:
                # Reserve this single dispatch before invoking. A pending
                # result-release ACK must never replay an already returned
                # setter; unknown dispatch errors quarantine the router.
                self._setter_done=context.signature
                try:self._invoke(catalog,root,'UserWidget','SetOwningPlayer',LocalPlayerController=pc)
                except RuntimeQueryError as error:
                    if getattr(error,'outcome',None)=='not_dispatched' and getattr(error,'native_error',None)==218:
                        # Loading retired the argument between proof and native
                        # dispatch. Never replay against this context. A future
                        # different controller/world must pass the full proof.
                        self._rejected_setter_context=context.signature
                        raise UiProofPending('Loading controller retired before UI ownership dispatch') from None
                    raise
                matched=readback()
            if not matched:
                raise UiProofMismatch('Typed widget owning-player/local-player/world readback mismatch')
            current() # reject a generation switch during getter calls
            if rebind:
                # Old controller/world copies are discarded. The native menu
                # prepare cache already keys PC identity; explicitly revoke it.
                self.scope._session._menu_plan_cache=None
                panel.player=pc
                panel._planner.close()
                # Root, children, current context and unchanged metadata are
                # selected anew; no old PC/world catalog is merged here.
                metadata=panel_metadata(panel.catalog)
                metadata=refresh_panel_metadata(self.scope.pid,metadata,observed=catalog)
                # The complete leased hierarchy was already freshly read twice
                # above. Add only the remaining planner metadata/current PC;
                # dispatch still validates every owned target and argument.
                selectors=tuple(dict.fromkeys(identity(o)[1:] for o in (*metadata,pc)))
                fresh=catalog.with_observations(capture_complete(self.scope.pid,selectors))
                panel.catalog=fresh
                panel._functions.clear();panel._defaults.clear()
                panel._planner=panel.scope.invocation_planner(catalog=fresh,selected_results=True)
                panel._planner._require_stable_ui_identities=getattr(panel,'_metadata_stable_ui',False)
                if getattr(self,'prime',True):panel.prime_menu_plan()
            return True
