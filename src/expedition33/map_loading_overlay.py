"""Process-owned, noninteractive cover for assigned-map restoration.

The native loading gate owns presentation while a load is in flight. This
helper only constructs the opaque tree in advance and supplies its exact
identities. It never activates a CommonUI input owner or changes focus.
"""
import logging
from pathlib import Path
import time
from .widgets import OwnedMenuPanel, widget_definition_names

LOG = logging.getLogger(__name__)
ART_PATH = Path(__file__).resolve().parent / 'assets' / 'map-loading.png'
MAX_ART_BYTES = 8 * 1024 * 1024


def loading_art_path(path=None):
    """Validate a consuming mod's PNG, with the SDK artwork as a fallback."""
    path = ART_PATH if path is None else Path(path)
    try:
        if not 8 <= path.stat().st_size <= MAX_ART_BYTES:
            return None
        with path.open('rb') as source:
            if source.read(8) != b'\x89PNG\r\n\x1a\n':
                return None
    except OSError:
        return None
    return path


class MapLoadingOverlay(OwnedMenuPanel):
    Z_ORDER = 10000
    NAMES = ('Widget', 'UserWidget', 'CommonActivatableWidget', 'WidgetTree',
             'CanvasPanel', 'CanvasPanelSlot', 'Border', 'WidgetBlueprintLibrary',
             'GameplayStatics', 'ESlateVisibility', 'Vector2D', 'LinearColor',
             'Anchors', 'Create', 'SpawnObject', 'AddChildToCanvas', 'SetPosition',
             'SetSize', 'SetAnchors', 'SetBrushColor', 'SetVisibility',
             'AddToViewport', 'IsInViewport', 'RemoveFromParent',
             # Create.OwningPlayer remains a reflected PlayerController object
             # constraint even when its argument is None. A CDO selector copies
             # the class closure without enumerating live/retiring controllers.
             'Default__PlayerController', 'Default__Image', 'SetBrushResourceObject',
             'Default__KismetRenderingLibrary', 'ImportFileAsTexture2D', 'Texture2D')

    def __init__(self, session, context, *, art_path=None):
        super().__init__(session, controls=1, cached_construction=True, selected_results=True)
        self.context = context
        self.native_owned = False
        self.attached = False
        self.art_texture = self.art_image = None
        self.art_available = False
        self.art_path = art_path

    def build(self):
        from .catalog import capture_matching, capture_selected
        from .enums import describe_enums
        from .values import read_object_reference
        from ._metadata_stabilization import prepare_discovery
        from ._stable_lease import stabilize_owned_tree, rediscover_owned_tree
        if self.state != 'new':
            raise RuntimeError('Construct a loading cover once')
        self.state = 'building'
        started = time.perf_counter()

        def discover():
            catalog = capture_matching(self.scope.pid, names=widget_definition_names(self.NAMES))
            roots = capture_selected(self.scope.pid, (self.context.gi[1:],))
            return catalog.with_observations(roots)

        self.catalog, uncovered = prepare_discovery(self.scope._session, discover)
        self.metadata_uncovered_count = len(uncovered)
        self._metadata_stable_ui = True
        enum = self.catalog.find_path('/Script/UMG.ESlateVisibility', 'Enum')
        descriptor = describe_enums(self.catalog, (enum,))[enum.index]
        def visibility(name):
            return descriptor.value(self._one(m for m in descriptor.members
                if m.name.rsplit('::', 1)[-1] == name).name)
        self.invisible = visibility('HitTestInvisible')
        self.collapsed = visibility('Collapsed')
        self._planner = self.scope.invocation_planner(selected_results=True, catalog=self.catalog)
        self._planner._require_stable_ui_identities = True
        gi = self.catalog.by_index[self.context.gi[1]]
        # This verified constructible native class is used only as a UserWidget.
        # ActivateWidget, input modes and focus setters are deliberately absent.
        self.widget = self._construction_call(self._default('WidgetBlueprintLibrary'),
            self._function('WidgetBlueprintLibrary', 'Create'),
            WorldContextObject=gi, WidgetType=self._class('CommonActivatableWidget'),
            OwningPlayer=None).return_value
        self.tree, current = read_object_reference(self._planner._catalog, self.widget,
            self._class('UserWidget'), 'WidgetTree', project=True)
        if self.tree is None or self.tree.outer_index != self.widget.index:
            raise RuntimeError('Loading cover has no owned widget tree')
        if self.tree.serial == 0:
            stable, _ = stabilize_owned_tree(self.scope, current, self.widget,
                self.tree, self._class('UserWidget'))
            self.catalog, self.tree, current = rediscover_owned_tree(self.scope.pid,
                discover, self.widget, stable, self._class('UserWidget').index)
            self._planner.refresh_from(self.catalog)
        self._planner.adopt_observations(current)
        if self._root() is not None:
            raise RuntimeError('Loading cover tree was not empty')
        self.canvas = self._spawn('CanvasPanel')
        backdrop = self._spawn('Border')
        slot = self._place(backdrop, 0, 0, 0, 0)
        self._call(slot, 'CanvasPanelSlot', 'SetAnchors',
            InAnchors={'Minimum': {'X': 0., 'Y': 0.}, 'Maximum': {'X': 1., 'Y': 1.}})
        self._call(backdrop, 'Border', 'SetBrushColor',
            InBrushColor={'R': .008, 'G': .008, 'B': .008, 'A': 1.})
        self._prepare_art(gi)
        self._call(self.widget, 'Widget', 'SetVisibility', InVisibility=self.collapsed)
        self._mutate(self.scope.assign_object, self.tree, self._class('WidgetTree'),
            'RootWidget', self.canvas, expected=None, allow_mutation=True,
            catalog=self._planner._catalog)
        self.assigned = True
        root = self._root()
        if root is None or (root.index, root.serial, root.address) != (
                self.canvas.index, self.canvas.serial, self.canvas.address):
            raise RuntimeError('Loading cover root assignment readback failed')
        self.state = 'built'
        self.timings['prepare_ms'] = (time.perf_counter() - started) * 1000
        return self

    def _prepare_art(self, gi):
        """Import once during loading; preserve the opaque cover on safe failure."""
        path = loading_art_path(getattr(self, 'art_path', None))
        if path is None and getattr(self, 'art_path', None) is not None:
            path = loading_art_path()
        if path is None:
            LOG.warning('Loading artwork unavailable; using opaque loading cover')
            return
        started = time.perf_counter()
        try:
            texture = self._construction_call(self._default('KismetRenderingLibrary'),
                self._function('KismetRenderingLibrary', 'ImportFileAsTexture2D'),
                WorldContextObject=gi, Filename=str(path)).return_value
            if texture is None:
                LOG.warning('Loading artwork import returned no texture; using opaque loading cover')
                return
            self.art_texture = texture
            image = self._spawn('Image')
            self.art_image = image
            self._call(image, 'Widget', 'SetVisibility', InVisibility=self.collapsed)
            slot = self._place(image, 0, 0, 0, 0)
            self._call(slot, 'CanvasPanelSlot', 'SetAnchors',
                InAnchors={'Minimum': {'X': 0., 'Y': 0.}, 'Maximum': {'X': 1., 'Y': 1.}})
            self._call(image, 'Image', 'SetBrushResourceObject', ResourceObject=texture)
            self._call(image, 'Widget', 'SetVisibility', InVisibility=self.invisible)
            self.art_available = True
        except Exception as error:
            # An uncertain mutation retains the owner for ordinary SDK cleanup;
            # it must not be hidden as an optional-art fallback or replayed.
            if self.uncertain:
                raise
            LOG.warning('Loading artwork preparation rejected (%s); using opaque loading cover',
                type(error).__name__)
        finally:
            self.timings['art_prepare_ms'] = (time.perf_counter() - started) * 1000

    def native_bindings(self):
        if self.state != 'built' or self.uncertain:
            raise RuntimeError('Loading cover must be completely prepared')
        return (self.widget, self._function('Widget', 'SetVisibility'),
                self._function('UserWidget', 'AddToViewport'),
                self._function('Widget', 'IsInViewport'),
                self._function('Widget', 'RemoveFromParent'))

    def adopt_native(self):
        bindings = self.native_bindings()
        self.native_owned = True
        return bindings

    def release_native(self):
        """Call only after native close ACK removed its presentation reference."""
        self.native_owned = False

    def close(self):
        if self.native_owned:
            raise RuntimeError('Native loading presentation must close before its tree')
        if self.state == 'closed':
            return True
        if self.widget is not None and not self.uncertain:
            self._render_call(self.widget, 'Widget', 'RemoveFromParent')
        return self.close_owned_tree()
