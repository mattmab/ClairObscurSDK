"""Combined copied admission/UI observation, owned only by its read worker."""
from dataclasses import dataclass, replace
from types import SimpleNamespace
from . import RuntimeQueryError
from .catalog import capture_selected
from .values import read_values_many, read_object_reference
from .world_admission import WarmAdmissionObserver
from .ui_shell_proof import UiContext


@dataclass(frozen=True)
class UiAdmission:
    admission: object
    menu_ready: bool | None
    title_ready: bool | None = False
    title_token: tuple | None = None
    ui_context: UiContext | None = None
    prewarm_context: UiContext | None = None


class UiAdmissionObserver(WarmAdmissionObserver):
    def controller(self, catalog, gi):
        current=super().controller(catalog,gi)
        self._ui_controller=tuple(current['controller'])
        return current

    def observe(self):
        # A proven world binding keeps passive sampling on four fresh queries.
        # Do not call the fast method without a binding: its deliberate full
        # fallback dispatches self.observe(), which would otherwise recurse.
        admission=(super().observe_activation() if getattr(self,'_activation_binding',None) is not None
            else super().observe())
        if admission.state!='world_ready':
            if admission.state=='inactive' and admission.reason=='save_not_loaded':
                packet=self._title_observation(admission)
                if packet.title_ready is True or self._reader is None:return packet
                return replace(packet,prewarm_context=self._title_prewarm_context())
            return UiAdmission(admission,False if admission.state in ('loading','inactive') else None)
        try:
            with self._reader.bind():
                # Exact controller selected from the successful fresh double
                # admission, not another registry search. UI status is not
                # authority to construct widgets or mutate engine state.
                catalog=capture_selected(self.pid,(self._ui_controller[1:],))
                controller=catalog.by_index[self._ui_controller[1]]
                worlds=tuple(obj for obj in catalog.outer_chain(controller) if obj.class_name=='World')
                if len(worlds)!=1 or (worlds[0].pid,worlds[0].index,worlds[0].serial,worlds[0].address)!=admission.token[0]:
                    return UiAdmission(admission,None)
                values=read_values_many(catalog,(controller,),fields=('PauseMenuWidget',))[controller.index]
                owners=[key[0] for key in values.types if key[1]=='PauseMenuWidget']
                if len(owners)!=1:raise RuntimeQueryError('Current pause field is ambiguous or missing')
                pause,_=read_object_reference(catalog,controller,catalog.by_index[owners[0]],
                    'PauseMenuWidget',project=True)
                ready=pause is not None and pause.class_name=='WBP_PauseMenu_C'
                copied=UiContext('world',admission.token[0],admission.token[1],
                    tuple(self._ui_local_player),tuple(self._ui_controller))
                return UiAdmission(admission,ready,ui_context=copied)
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

    def _title_prewarm_context(self):
        """No borrowed title widget/input authority; verify engine/PC twice."""
        from .cinematics.history import anchor, identity
        from .cinematics.original_game_action import NotReady
        from .ui_shell_proof import TITLE_WORLD
        def once():
            chain,catalog=anchor(self.engine_catalog(),project=True)
            world,gi=chain[2:]
            if catalog.path_name(world)!=TITLE_WORLD:return None
            current=self.controller(catalog,gi)
            if tuple(current['world'])!=identity(world):return None
            selected=capture_selected(self.pid,(current['controller'][1:],))
            pc=selected.by_index[current['controller'][1]]
            if pc.class_name!='BP_jRPG_Controller_MainMenu_C' or pc.object_flags&0x30:return None
            local,selected=read_object_reference(selected,pc,selected.find_class('PlayerController'),
                'Player',project=True)
            if local is None or identity(local)!=tuple(self._ui_local_player):return None
            worlds=[o for o in selected.outer_chain(pc) if o.class_name=='World']
            if len(worlds)!=1 or identity(worlds[0])!=identity(world):return None
            return UiContext('title',identity(world),identity(gi),identity(local),identity(pc))
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
