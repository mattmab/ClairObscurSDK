"""Prepare the pause entry while loading; mod activation adopts its owner."""
from expedition33._scope import SessionScope
from expedition33.pause_menu import PauseMenuEntry


class LoadingEntry:
    def __init__(self,mod,session):
        self.mod=mod;self.session=session;self.scope=SessionScope(session,lease_owner='MapTravelLoadingUI')
        self.entry=None;self.context=None;self.adopted=False

    @property
    def released(self):
        return (self.context is not None or self.adopted) and (self.entry is None or self.entry.state=='closed')

    def prepare(self,context):
        self.mod._loading_entry=self
        self.mod._loading_routes=None
        self._routes()

    def _routes(self):
        from expedition33.zone_travel import routes
        from expedition33.cinematics.original_game_action import NotReady
        if self.mod._loading_routes is None:
            try:self.mod._loading_routes=routes(self.session.pid)
            except NotReady:pass # Pure table discovery can precede asset load.

    def bind(self,context,*,preparing=False):
        if self.adopted:return
        self._routes()
        if self.context is not None and self.context.signature!=context.signature:
            if not self._retire():return
        ready=getattr(self.session,'_menu_readiness',None)
        if not callable(ready) or ready() is not True:return
        if self.entry is None:
            from . import MapView
            native=self.session._native_menu_service.for_view(lambda registry:MapView(registry,self.mod))
            self.context=context
            self.entry=PauseMenuEntry(self.scope,native,label='Map Travel',readiness=ready)
            self.entry._expected_controller=context.controller
        if self.entry.state=='new':
            from expedition33 import RuntimeQueryError
            try:self.entry.install()
            except RuntimeQueryError as error:
                # No widget/lease exists before install enters building. Asset
                # discovery can race loading GC; discard only that pure read.
                if self.entry.state=='new' and any(code in str(error) for code in
                    ('READ_FAILED','REFLECTION_TARGET_CHANGED','DESCRIPTOR_IDENTITY_CHANGED','MATCH_TYPE_NOT_REGISTERED')):
                    return
                raise
        # No click delivery, mod callback, or travel is serviced before adoption.

    def _retire(self):
        if self.entry is not None and self.entry.state not in ('new','closed'):
            if self.entry.retire_world()!='ack':return False
        self.entry=None;self.context=None
        return True

    def observe_title(self,context):
        if not self.adopted and self.context is not None:
            previous=self.context
            if self._retire():self.context=previous # Publish released owner to coordinator.

    def close(self):
        if self.entry is not None and self.entry.state not in ('new','closed'):
            raise RuntimeError('Loading pause entry retirement has not acknowledged')
        if not self.scope._closed:self.scope.close()
