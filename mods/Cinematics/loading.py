"""Prepare reusable cinematic dependencies before gameplay activation."""
from expedition33._scope import SessionScope
from expedition33._cinematic_panel_pool import CinematicDependencies,CinematicPanelPool
from expedition33.ui_shell_proof import UiProofPending


class LoadingReplay:
    def __init__(self,mod,session):
        self.mod=mod;self.session=session;self.dependencies=None;self.pool=None
        self.signature=None;self.adopted=False;self.released=False
        self.history=None;self.reader=None
        self.pause=None;self.scope=SessionScope(session,lease_owner='CinematicLoadingUI')

    def prepare(self,context):
        self.mod._loading_replay=self
        self.dependencies=CinematicDependencies(self.session,context.gi)
        self.dependencies.prepare()

    def observe_title(self,context):
        self._retire_pool()
        self.bind_dependencies(context)

    def bind_dependencies(self,context):
        if self.dependencies.gi!=context.gi:
            raise RuntimeError('Cinematic preparation belongs to another GameInstance')

    def _retire_pool(self):
        if self.pause is not None:
            if self.pause.retire_world()!='ack':raise UiProofPending('Cinematic pause entry retirement pending')
            self.pause=None
        if self.pool is not None:
            if self.pool.retire_world()!='ack':raise UiProofPending('Cinematic loading panel retirement pending')
            self.pool=None;self.signature=None;self.adopted=False
            self.history=None
        if self.reader is not None:self.reader.close();self.reader=None

    def bind(self,context,*,preparing=False):
        self.bind_dependencies(context)
        if self.signature==context.signature:
            self._prepare_pause(context);return
        self._retire_pool()
        # A loading packet authorizes detached construction, never playback.
        if context.kind!='world':return
        self.pool=CinematicPanelPool(self.session,dependencies=self.dependencies)
        self.signature=context.signature
        self.pool.prepare()
        from expedition33.cinematics.history import PreparedHistorySelectors
        from expedition33._reader import ReadBatch
        self.history=PreparedHistorySelectors(self.pool.scope)
        self.reader=ReadBatch(self.session.pid,share=True,_executable=self.session._transport._executable)
        self.reader.warm()
        self._prepare_pause(context)

    def _prepare_pause(self,context):
        if self.adopted:return
        if self.pause is None:self.pause=self.mod.prepare_loading_pause(self.scope)
        self.pause._expected_controller=context.controller
        if self.pause.state in ('new','prepared'):
            from expedition33 import RuntimeQueryError
            try:self.pause.install()
            except RuntimeQueryError as error:
                # This is only the pre-construction read, never a replay of an
                # invocation or a partially built tree.
                if self.pause.state in ('new','prepared') and any(code in str(error) for code in
                        ('READ_FAILED','REFLECTION_TARGET_CHANGED','DESCRIPTOR_IDENTITY_CHANGED','MATCH_TYPE_NOT_REGISTERED')):
                    raise UiProofPending('Cinematic pause discovery changed during loading') from None
                raise
        if self.pause.state!='attached':raise UiProofPending('Cinematic pause entry awaits the destination menu')

    def take(self,session):
        if self.pool is None or self.pool.closed or self.adopted:return None
        if self.pause is None or self.pause.state!='attached':
            raise UiProofPending('Cinematic pause entry is not ready for adoption')
        from expedition33.cinematics.controller_anchor import context_observer
        if session._session is not self.session or context_observer(self.pool.scope)()!=self.pool.context:
            raise RuntimeError('Prepared cinematic panel does not match activation')
        self.adopted=True
        return self.pool

    def take_reader(self):
        reader,self.reader=self.reader,None
        return reader

    def close(self):
        self._retire_pool()
        if self.dependencies is not None and not self.dependencies.close():
            raise UiProofPending('Cinematic preparation lease release pending')
        if not self.scope._closed:self.scope.close()
