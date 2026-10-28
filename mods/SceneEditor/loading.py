"""Independently owned, non-playing cinematic preparation for Scene Editor."""
from expedition33._cinematic_panel_pool import CinematicDependencies
from expedition33.ui_shell_proof import UiProofPending


def validate_dependencies(dependencies,scope,context):
    """Compare freshly read world and both retained service GIs before use."""
    from expedition33.cinematics.history import identity
    dependencies.validate(scope,context)
    for provider in (dependencies.widget_dependencies,dependencies.music_dependencies):
        catalog=provider.capture(scope)
        matches=tuple(o for o in catalog.objects if o.class_name=='BP_jRPG_GI_Custom_C'
                      and not o.name.startswith('Default__'))
        if len(matches)!=1 or identity(matches[0])!=dependencies.gi:
            raise RuntimeError('Prepared cinematic service GameInstance changed')


class LoadingPreview:
    # The loader can recreate this owner for a destination after retirement.
    reprepare_on_world_change=True

    def __init__(self,mod,session):
        self.mod=mod;self.session=session;self.dependencies=None
        self.context=None;self.retiring=False;self.released=False;self.closed=False

    def prepare(self,context):
        self.mod._scene_loading=self
        self.context=context
        # Journal the owner before preparing: a partially prepared scope still
        # requires acknowledged lease cleanup if preparation fails.
        self.dependencies=CinematicDependencies(self.session,context.gi)
        self.dependencies.prepare()

    def bind(self,context,*,preparing=False):
        if self.closed or self.released:return
        if self.retiring:
            self.close()
            raise UiProofPending('Scene Editor cinematic preparation was retired')
        if self.dependencies is None or self.dependencies.gi!=context.gi:
            # The coordinator's released-owner close is not a pending boundary.
            # Publish released only after the scoped lease close acknowledges.
            self.close()
            raise UiProofPending('Scene Editor cinematic preparation belongs to another GameInstance')
        self.context=context

    def observe_title(self,context):
        if not self.closed and (self.retiring or
                (self.dependencies is not None and self.dependencies.gi!=context.gi)):
            self.close()

    def available(self,session):
        dependencies=self.dependencies
        if (self.closed or self.retiring or self.released or dependencies is None or not dependencies.ready or
                session._session is not self.session):
            return None
        return dependencies

    def _has_consumer(self):
        preview=getattr(self.mod,'authored_preview',None)
        return (preview is not None and not preview.closed and
                getattr(preview,'dependencies',None) is self.dependencies)

    def close(self):
        if self.closed:return
        # Close may release only part of a bundle before deferring. Stop lending
        # it immediately, including if the user cancels a pending disable.
        self.retiring=True
        if self._has_consumer():
            raise UiProofPending('Scene Editor preview still owns cinematic dependencies')
        if self.dependencies is not None and not self.dependencies.close():
            raise UiProofPending('Scene Editor cinematic preparation release pending')
        self.closed=True;self.released=True
        if getattr(self.mod,'_scene_loading',None) is self:self.mod._scene_loading=None

    def release(self):
        self.close()
