"""Minimal reusable input/context tree for an SDK-owned cinematic player.

The native sequence factory still requires a freshly attached menu owner and
its current controller. This panel keeps only the UObject tree between scenes;
hide() releases input/viewport/Slate ownership before combat starts. It is never
a visible mod menu and contains no labels, art widgets or reusable row layout.
"""
from .widgets import OwnedMenuPanel


class CinematicContextPanel(OwnedMenuPanel):
    BATCH_CONSTRUCTION = True
    EXTRA_NAMES = ('SetRenderOpacity',)
    # This invisible input owner constructs no text, art or scrolling widgets.
    # Keep native focus/schema qualification, without discovering their unused
    # Blueprint classes, style metadata and reflected setters on every replay.
    DISCOVERY_NAMES = (
        'Widget','UserWidget','CommonActivatableWidget','WidgetTree',
        'CanvasPanel','CanvasPanelSlot','Button','Border',
        'WidgetBlueprintLibrary','GameplayStatics','Default__WidgetBlueprintLibrary','Default__GameplayStatics',
        'ESlateVisibility','Vector2D','LinearColor','Anchors','EMouseLockMode',
        'Create','SpawnObject','AddChildToCanvas','SetPosition','SetSize','SetAnchors',
        'SetIsEnabled','SetVisibility','SetBrushColor','AddToViewport','IsInViewport',
        'ActivateWidget','IsActivated','SetUserFocus','HasKeyboardFocus','HasUserFocus',
        'DeactivateWidget','RemoveFromParent','SetFocusToGameViewport',
        'SetInputMode_UIOnlyEx','SetInputMode_GameOnly',
    )

    def __init__(self, session):
        super().__init__(session, controls=1, cached_construction=True, selected_results=True)

    def _build_contents(self):
        button = self._spawn('Button')
        self._place(button, 0, 0, 1, 1)
        self.buttons.append(button)
        self._visible[0] = True
        self._enabled[0] = True

    def build(self):
        super().build()
        # An intentional permanently invisible context panel has no temporary
        # opacity to restore between scenes. Native focus remains explicit.
        self._render_call(self.widget, 'Widget', 'SetRenderOpacity', InOpacity=0.)
        return self
