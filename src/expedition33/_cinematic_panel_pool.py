"""One detached cinematic tree per admitted world; fresh input ownership per play."""
from ._scope import SessionScope
from .assets import PreparedAssetLoader
from ._sequence_metadata import PreparedSequenceMetadata
from ._reader import shared_operation
from ._retired_tracking import close_lease_only_scope
from .cinematics.controller_anchor import context_observer
from .cinematic_context_panel import CinematicContextPanel
from .cinematics.title_adapters import prepare_widget_routing,PreparedWidgetDependencies,PreparedMusicDependencies


class CinematicDependencies:
    """GI and retained metadata only; no world/controller/widget/input owner."""
    def __init__(self,session,gi):
        self.scope=SessionScope(session,lease_owner='CinematicPreparation')
        self.gi=gi;self.ready=False

    def prepare(self):
        if self.ready:raise RuntimeError('Prepare cinematic dependencies once')
        with shared_operation(self.scope.pid,_executable=self.scope._session._transport._executable):
            self.routing_class=prepare_widget_routing(self.scope)
            self.widget_dependencies=PreparedWidgetDependencies(self.scope)
            self.asset_loader=PreparedAssetLoader(self.scope)
            self.sequence_metadata=PreparedSequenceMetadata(self.scope)
            self.music_dependencies=PreparedMusicDependencies(self.scope)
        self.ready=True

    def validate(self,scope,context):
        self.scope._check();scope._check()
        if not self.ready or scope._session is not self.scope._session:
            raise RuntimeError('Cinematic preparation is not ready for this SDK session')
        from .values import capture_selected_values
        from .cinematics.history import identity,field
        catalog,values=capture_selected_values(scope.pid,(context['world'][1:],),fields=('OwningGameInstance',),references=True)
        world=catalog.by_index[context['world'][1]]
        if identity(field(values[world.index],'OwningGameInstance','ObjectProperty'))!=self.gi:
            raise RuntimeError('Cinematic preparation GameInstance changed')

    def close(self):return close_lease_only_scope(self.scope)


class CinematicPanelPool:
    def __init__(self,session,*,dependencies=None):
        self.scope=SessionScope(session)
        self.dependencies=dependencies
        self.panel=self.context=None
        self.routing_class=None
        self.widget_dependencies=None
        self.asset_loader=None
        self.sequence_metadata=None
        self.music_dependencies=None
        self.in_use=self.closed=self.retiring=False

    def prepare(self):
        self.scope._check()
        if self.closed or self.retiring or self.in_use or self.panel is not None:
            raise RuntimeError('Prepare a cinematic panel pool only once')
        with shared_operation(self.scope.pid,_executable=self.scope._session._transport._executable):
            observe=context_observer(self.scope)
            self.context=observe()
            self.panel=CinematicContextPanel(self.scope)
            self.panel.build()
            if self.dependencies is not None:
                self.dependencies.validate(self.scope,self.context)
                for name in ('routing_class','widget_dependencies','asset_loader','sequence_metadata','music_dependencies'):
                    setattr(self,name,getattr(self.dependencies,name))
            else:
                self.routing_class=prepare_widget_routing(self.scope)
                self.widget_dependencies=PreparedWidgetDependencies(self.scope)
                self.asset_loader=PreparedAssetLoader(self.scope)
                self.sequence_metadata=PreparedSequenceMetadata(self.scope)
                self.music_dependencies=PreparedMusicDependencies(self.scope)
            if observe()!=self.context:
                self.retiring=True
                raise RuntimeError('World changed while preparing cinematic panel')

    def acquire(self,context):
        self.scope._check()
        if self.closed or self.retiring or self.in_use or self.panel is None:
            raise RuntimeError('Cinematic panel is unavailable')
        if context!=self.context:
            self.retiring=True
            raise RuntimeError('Prepared cinematic panel belongs to another world or controller')
        if self.panel.state!='built' or self.panel.uncertain:
            raise RuntimeError('Prepared cinematic panel is not safely detached')
        self.in_use=True
        return self.panel

    def release(self,panel,*,retired=False):
        if panel is not self.panel or not self.in_use:
            raise RuntimeError('Unrelated cinematic panel release')
        if retired:
            self.retiring=True
            result=self.panel.retire_world()
            if result=='pending':return False
            if result!='ack':raise RuntimeError('Cinematic panel retirement is uncertain')
        elif not self.panel.hide():return False
        self.in_use=False
        return True

    def retire_world(self):
        if self.closed:return 'ack'
        self.retiring=True
        if self.in_use:return 'pending'
        if self.panel is not None:
            result=self.panel.retire_world()
            if result!='ack':return result
        if not close_lease_only_scope(self.scope):return 'pending'
        self.closed=True
        return 'ack'

    def close(self):
        if self.closed:return True
        if self.retiring:return self.retire_world()=='ack'
        if self.in_use:raise RuntimeError('Close the cinematic consumer before its panel pool')
        if self.panel is not None and not self.panel.close_owned_tree():return False
        if not close_lease_only_scope(self.scope):return False
        self.closed=True
        return True
