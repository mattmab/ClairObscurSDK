"""Combined copied admission/UI observation, owned only by its read worker."""
from dataclasses import dataclass, replace
from types import SimpleNamespace
from . import RuntimeQueryError
from .catalog import capture_selected
from .values import read_object_reference, capture_selected_values
from .world_admission import WarmAdmissionObserver, _projected_reference
from .ui_shell_proof import UiContext


@dataclass(frozen=True)
class UiAdmission:
    admission: object
    menu_ready: bool | None
    title_ready: bool | None = False
    title_token: tuple | None = None
    ui_context: UiContext | None = None
    prewarm_context: UiContext | None = None
    activation_selectors: tuple | None = None
    bootstrap_ready: bool = False
    layer_selectors: object | None = None


class UiAdmissionObserver(WarmAdmissionObserver):
    def __init__(self,pid,*,layer_preparation=None):
        super().__init__(pid)
        self._layer_preparation=layer_preparation;self._layer_observer=None;self._layer_selectors=None

    def observe_anchored_world(self,catalog,chain):
        requested=getattr(self,'_layer_preparation',None)
        if requested is None or not requested.is_set():
            self._layer_observer=None;self._layer_selectors=None;return
        if self._layer_observer is None:
            from .story_layers import LayerSelectorObserver
            self._layer_observer=LayerSelectorObserver(self.pid)
        self._layer_selectors=self._layer_observer.observe(catalog,chain)

    def controller(self, catalog, gi):
        current=super().controller(catalog,gi)
        self._ui_controller=tuple(current['controller'])
        return current

    def observe(self):
        packet=self._observe()
        # Even a missing/racing pause widget must not force the owner thread to
        # rediscover the world. These selectors grant no admission: the owner
        # re-reads the entire binding twice before every activation.
        return replace(packet,activation_selectors=(getattr(self,'_observed_activation_selectors',None)
            if packet.admission.activation_ready else None),layer_selectors=getattr(self,'_layer_selectors',None))

    def _observe(self):
        # A proven world binding keeps passive sampling on four fresh queries.
        # Do not call the fast method without a binding: its deliberate full
        # fallback dispatches self.observe(), which would otherwise recurse.
        admission=(super().observe_activation() if getattr(self,'_activation_binding',None) is not None
            else super().observe())
        self._observed_activation_selectors=getattr(self,'_activation_binding',None)
        if admission.state!='world_ready':
            if ((admission.state=='inactive' and admission.reason=='save_manager_unavailable')
                    or (admission.state=='loading' and admission.reason=='save_load_in_progress')):
                # Detached title preparation needs the verified engine/GI/LP/PC,
                # not a save manager or borrowed title widgets. The independent
                # double proof rejects gameplay worlds and changed identities.
                context=self._title_prewarm_context() if self._reader is not None else None
                if context is None and self._reader is not None:
                    context=self._detached_prewarm_context('world')
                return self._prewarm_packet(admission,context)
            if admission.state=='inactive' and admission.reason=='save_not_loaded':
                packet=self._title_observation(admission)
                if packet.title_ready is True or self._reader is None:return packet
                context=self._title_prewarm_context()
                if context is None:context=self._detached_prewarm_context('world')
                prepared=self._prewarm_packet(admission,context)
                return replace(prepared,title_ready=packet.title_ready,title_token=packet.title_token)
            context=(self._detached_prewarm_context('world')
                if getattr(self,'_reader',None) is not None and admission.state in ('loading','observation_pending') else None)
            if context is not None:return self._prewarm_packet(admission,context)
            return UiAdmission(admission,False if admission.state in ('loading','inactive') else None)
        try:
            with self._reader.bind():
                # Exact controller selected from the successful fresh double
                # admission, not another registry search. UI status is not
                # authority to construct widgets or mutate engine state.
                pause=self._pause_menu(self._ui_controller,admission.token[0])
                if pause is None:return UiAdmission(admission,None)
                ready,field_present=pause
                copied=UiContext('world',admission.token[0],admission.token[1],
                    tuple(self._ui_local_player),tuple(self._ui_controller))
                if not field_present:return UiAdmission(admission,False,prewarm_context=copied)
                return UiAdmission(admission,ready,ui_context=copied,
                    prewarm_context=copied if not ready or not admission.activation_ready else None,
                    activation_selectors=getattr(self,'_activation_binding',None))
        except RuntimeQueryError as error:
            self._discard()
            if any(reason in str(error) for reason in ('READ_FAILED',
                    'Object identity changed or belongs to another process',
                    'Object property reference changed during observation')):
                return UiAdmission(admission,None)
            raise
        except BaseException:
            self._discard()
            raise

    def _pause_menu(self,controller_identity,world_identity):
        # One fresh projection supplies both the controller's outer world and
        # its widget reference. No second value read merely to learn its owner.
        catalog,rows=capture_selected_values(self.pid,(tuple(controller_identity[1:]),),
            fields=('PauseMenuWidget',),references=True)
        controller=catalog.by_index[controller_identity[1]]
        worlds=tuple(obj for obj in catalog.outer_chain(controller) if obj.class_name=='World')
        if len(worlds)!=1 or (worlds[0].pid,worlds[0].index,worlds[0].serial,worlds[0].address)!=world_identity:
            return None
        observed=rows[controller.index]
        if len([key for key in observed.types if key[1]=='PauseMenuWidget'])!=1:return False,False
        pause=_projected_reference(catalog,observed,controller,'PauseMenuWidget')
        return pause is not None and pause.class_name=='WBP_PauseMenu_C',True

    def _prewarm_packet(self,admission,context):
        # SaveLoaded may still be false after the new world/controller and its
        # pause widget exist. This grants UI preparation only, never activation.
        if context is not None and getattr(context,'kind',None)=='title':
            # The authored frontend can already exist while the save manager
            # still reports loading. Its own fresh authority proof, rather than
            # a gameplay save flag, decides when the title entry can attach.
            title=self._title_observation(admission)
            if title.title_ready is True:
                return replace(title,ui_context=context,prewarm_context=context)
            return replace(title,prewarm_context=context)
        ready=False
        if context is not None and getattr(context,'kind',None)=='world':
            with self._reader.bind():
                pause=self._pause_menu(context.controller,context.world)
                if pause is not None:ready=pause[0]
        bootstrap=(context is not None and getattr(context,'kind',None)=='world' and
            context.world==getattr(self,'_bootstrap_world',None) and not admission.activation_ready)
        return UiAdmission(admission,ready,prewarm_context=context,bootstrap_ready=bootstrap)

    def _title_prewarm_context(self):
        """No borrowed title widget/input authority; verify engine/PC twice."""
        return self._detached_prewarm_context('title')

    def _detached_prewarm_context(self,kind):
        from .cinematics.history import anchor, identity
        from .cinematics.original_game_action import NotReady
        from .ui_shell_proof import TITLE_WORLD
        def once():
            chain,catalog=anchor(self.engine_catalog(),project=True)
            world,gi=chain[2:]
            world_path=catalog.path_name(world)
            if (world_path==TITLE_WORLD)!=(kind=='title'):return None
            if world_path=='/Game/Levels/Map_Game_Bootstrap.Map_Game_Bootstrap':self._bootstrap_world=identity(world)
            current=self.controller(catalog,gi)
            if tuple(current['world'])!=identity(world):return None
            selected=capture_selected(self.pid,(current['controller'][1:],))
            pc=selected.by_index[current['controller'][1]]
            if pc.object_flags&0x30:return None
            if (pc.class_name=='BP_jRPG_Controller_MainMenu_C')!=(kind=='title'):return None
            owner=selected.by_index[selected.find_class('PlayerController').index]
            local,selected=read_object_reference(selected,pc,owner,
                'Player',project=True)
            if local is None or identity(local)!=tuple(self._ui_local_player):return None
            worlds=[o for o in selected.outer_chain(pc) if o.class_name=='World']
            if len(worlds)!=1 or identity(worlds[0])!=identity(world):return None
            return UiContext(kind,identity(world),identity(gi),identity(local),identity(pc))
        try:
            with self._reader.bind():
                first=once()
                if first is None:return None
                second=once()
                return second if first==second else None
        except NotReady:return None
        except RuntimeError as error:
            # Same exact loading/null-anchor outcomes as ordinary admission.
            # A title/save transition can invalidate this additional proof
            # after its preceding sample; schema/programming errors still raise.
            if str(error) in ('Current history context reference is null',
                    'Current history context is ambiguous or unavailable',
                    'Active world has no verified game instance'):
                return None
            raise

    def _title_observation(self, admission):
        from .title_menu import resolve_title_context, title_authority_current
        from .cinematics.original_game_action import NotReady
        scope=SimpleNamespace(pid=self.pid)
        def identity(obj):return obj.index,obj.serial,obj.address
        try:
            with self._reader.bind():
                binding=getattr(self,'_title_binding',None)
                if binding is None:
                    found=resolve_title_context(scope,local_identity=getattr(self,'_title_local',None))
                    if found is None:return UiAdmission(admission,False,False)
                    if found['context']['world_path']!='/Game/Levels/UI/MainMenu/Level_MainMenu.Level_MainMenu':
                        return UiAdmission(admission,False,False)
                    self._title_local=identity(found['local_player'])
                    binding=(found['context'],self._title_local,
                        identity(found['main']),identity(found['title']),identity(found['box']))
                # Binding contains selectors only: both reads and every link
                # are freshly validated by the compact authority helper.
                if not title_authority_current(scope,binding):
                    self._title_binding=None
                    return UiAdmission(admission,False,None)
                self._title_binding=binding
                token=(tuple(binding[0]['world']),tuple(binding[0]['controller']),*binding[1:])
            chain=getattr(self,'_ui_anchor',None)
            copied=None
            if chain is not None and tuple(chain[2])==tuple(binding[0]['world']):
                copied=UiContext('title',tuple(chain[2]),tuple(chain[3]),
                    (self.pid,*binding[1]),tuple(binding[0]['controller']))
            return UiAdmission(admission,False,True,token,copied)
        except NotReady:
            return UiAdmission(admission,False,None)
        except RuntimeQueryError as error:
            self._discard()
            if any(reason in str(error) for reason in ('READ_FAILED',
                    'Object identity changed or belongs to another process',
                    'Object property reference changed during observation',
                    'DESCRIPTOR_IDENTITY_CHANGED', 'SELECTED_DEPENDENCY_CHANGED')):
                return UiAdmission(admission,False,None)
            raise

    def _discard(self):
        self._title_local=None
        self._title_binding=None
        super()._discard()
