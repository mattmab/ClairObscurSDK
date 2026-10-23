"""Detached, GameInstance-owned catalog/HUD prepared before gameplay activation."""
from expedition33._scope import SessionScope
from expedition33._reader import ReadBatch,active_reader
from expedition33.ui_shell_proof import OwnedUiProof,UiProofPending,prepare_panel_metadata

class LoadingUI:
    def __init__(self,mod,session):
        self.mod=mod
        self.scope=SessionScope(session,lease_owner='WorldBuilderLoadingUI')
        self.catalog=self.hud=None;self.context=None;self.bound=None
        self.proofs=[]

    @property
    def released(self):
        return self.context is not None and all(panel is not None and panel.state=='closed'
            for panel in (self.catalog,self.hud))

    def prepare(self,context):
        from .library import Library
        from .hud import BuilderHUD
        from .catalog_menu import CatalogMenu
        previous=self.mod.session
        self.mod.session=self.scope
        try:
            self.mod.library=Library(self.mod)
            # Create both roots while the verified title controller is current.
            # Neither build attaches a viewport nor captures keyboard input.
            self.hud=BuilderHUD(self.scope,self.mod.help_minimized)
            self.catalog=CatalogMenu(self.mod)
            with ReadBatch(self.scope.pid,share=active_reader() is None):
                self.hud.build()
                self.catalog.build()
                prepare_panel_metadata(self.catalog)
                prepare_panel_metadata(self.hud)
                self.proofs=[OwnedUiProof(self.scope,panel_type=type(self.catalog)),
                             OwnedUiProof(self.scope,panel_type=type(self.hud),prime=False)]
                # Admit getter schemas while loading, before gameplay exists.
                self.context=context
                try:
                    for panel,proof in zip((self.catalog,self.hud),self.proofs):
                        proof.verify(panel,context,preparing=context.kind=='world')
                except UiProofPending:
                    # A fast Continue can end title during construction. Keep
                    # both detached owners; bind() proves the next context.
                    pass
        finally:self.mod.session=previous

    def bind(self,context,*,preparing=False):
        if self.bound==context.signature:return
        if self.context is None:raise UiProofPending('World Builder detached preparation is incomplete')
        with ReadBatch(self.scope.pid,share=active_reader() is None):
            for panel,proof in zip((self.catalog,self.hud),self.proofs):
                proof.verify(panel,context,rebind=True,preparing=preparing)
        self.bound=context.signature

    def observe_title(self,context):
        # A loading GC may have interrupted only the final read-only proof.
        # Re-prove the existing detached trees, without rebuilding or replaying
        # construction, before the user selects the next save.
        if not self.released:self.bind(context)

    def close(self):
        for panel in (self.catalog,self.hud):
            if panel is not None and panel.state!='closed':panel.close()
        if not self.scope._closed:self.scope.close()
        if self.mod._loading_ui is self:self.mod._loading_ui=None
