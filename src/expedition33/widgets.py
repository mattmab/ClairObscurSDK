"""Owned native UMG panel built from the verified base-widget paths.

Experimental v17 renderer infrastructure. No game assets, stock offsets, input
mode resets, research-script imports or independent controller are used here.
Construction is explicit so callers retain the owner even if a mutation fails.
"""
import logging
import time
from contextlib import contextmanager

from .catalog import capture, capture_selected, capture_matching
from .enums import describe_enums
from .values import read_values, read_object_reference
from ._scope import SessionScope


class OwnedMenuPanel:
    EXTRA_NAMES = ()

    def __init__(self, session, *, controls=12, cached_construction=False, selected_results=False):
        session._check()
        if not session.supports_multi_controls:
            raise ValueError('Owned menu panels require v17 multi-control support')
        if type(controls) is not int or not 1 <= controls <= 64:
            raise ValueError('A panel requires between1 and64 controls')
        if type(cached_construction) is not bool:
            raise ValueError('cached_construction must be bool')
        if type(selected_results) is not bool or (selected_results and not cached_construction):
            raise ValueError('selected_results requires cached_construction')
        self._cached_construction = cached_construction
        self._selected_results = selected_results
        self.scope = SessionScope(session)
        self.count = controls
        self.state = 'new'
        self.menu = None
        self.widget = self.tree = self.canvas = None
        self.buttons, self.labels, self.children = [], [], []
        self.button_art = []
        self.assigned = False
        self.uncertain = False
        self._text = {}
        self._enabled = {}
        self._visible = {}
        self._planner = None
        self._functions = {}
        self._defaults = {}
        self._paint_queue = None
        self._layout_queue = None
        self.timings = {}

    @contextmanager
    def paint_batch(self):
        from . import _ui_batch
        if self._planner is None or not _ui_batch.available(self.scope._session):
            yield
            return
        if self._paint_queue is not None:
            raise RuntimeError('Menu paint batches cannot be nested')
        self._paint_queue = []
        try:
            yield
            # Sparse views may change all three setters on each reusable row.
            # Preserve the native bound and stop immediately if a group fails.
            for start in range(0, len(self._paint_queue), _ui_batch.LIMIT):
                self._mutate(_ui_batch.invoke_setters, self.scope,
                             self._paint_queue[start:start + _ui_batch.LIMIT])
        except BaseException:
            self._text.clear(); self._enabled.clear(); self._visible.clear()
            raise
        finally:
            self._paint_queue = None

    @staticmethod
    def _one(rows):
        rows = tuple(rows)
        if len(rows) != 1:
            raise ValueError('Expected one target-build widget identity')
        return rows[0]

    def _function(self, owner, name):
        key = (owner, name)
        if key in self._functions:
            return self._functions[key]
        owner_index = self._class(owner).index
        result = self._one(o for o in self.catalog.objects
            if o.outer_index == owner_index and o.name == name)
        self._functions[key] = result
        return result

    def _class(self, name):
        return self.catalog.by_index[self.catalog.find_class(name).index]

    def _default(self, name):
        if name in self._defaults:
            return self._defaults[name]
        class_index = self._class(name).index
        result = self._one(o for o in self.catalog.objects
            if o.class_index == class_index and o.name == 'Default__' + name)
        self._defaults[name] = result
        return result

    def _mutate(self, method, *args, **kwargs):
        if self.uncertain:
            raise RuntimeError('Widget mutation outcome unknown; no retry is permitted')
        self.uncertain = True
        result = method(*args, **kwargs)
        self.uncertain = False
        return result

    def _call(self, obj, owner, name, **args):
        if self.state == 'building' and self._planner is not None:
            if self._layout_queue is not None:
                # Store arguments, not PreparedInvocations: each object creation
                # revokes the previous planning generation. All targets remain
                # owned and the detached tree is not exposed until flush succeeds.
                self._layout_queue.append((obj, owner, name, args))
                return
            with self._construction_call(obj, self._function(owner, name), **args):
                pass
            return
        return self._mutate(self.scope.invoke, obj, self._function(owner, name), **args)

    def _construction_call(self, obj, function, **arguments):
        if self._planner is None:
            return self._mutate(self.scope.invoke_retained, obj, function, **arguments)
        prepared = self._planner.prepare(obj, function, **arguments)
        # Creation returns were already captured and decoded under native leases.
        # Reuse that catalog, never synthesize entries for newly created objects.
        return self._mutate(prepared.invoke, refresh_from_result=True)

    def _spawn(self, name):
        return self._construction_call(
            self._default('GameplayStatics'), self._function('GameplayStatics', 'SpawnObject'),
            ObjectClass=self._class(name), Outer=self.tree).return_value

    def _place(self, child, x, y, width, height):
        slot = self._construction_call(self.canvas,
            self._function('CanvasPanel', 'AddChildToCanvas'), Content=child).return_value
        self.children.append(child)
        self._call(slot, 'CanvasPanelSlot', 'SetPosition', InPosition={'X':float(x),'Y':float(y)})
        self._call(slot, 'CanvasPanelSlot', 'SetSize', InSize={'X':float(width),'Y':float(height)})
        self._call(slot, 'CanvasPanelSlot', 'SetAnchors',
            InAnchors={'Minimum':{'X':0.0,'Y':0.0},'Maximum':{'X':0.0,'Y':0.0}})
        return slot

    def _label(self, x, y, width, height, *, centered=False):
        label = self._spawn('CommonTextBlock')
        self._call(label, 'CommonTextBlock', 'SetStyle',
            InStyle=self._class('CTS_B1_SmallLine_Outline_C'))
        if centered:
            frame = self._spawn('Overlay')
            self._place(frame, x, y, width, height)
            slot = self._construction_call(frame,
                self._function('Overlay', 'AddChildToOverlay'), Content=label).return_value
            self._call(slot, 'OverlaySlot', 'SetHorizontalAlignment', InHorizontalAlignment=2)
            self._call(slot, 'OverlaySlot', 'SetVerticalAlignment', InVerticalAlignment=2)
            self._call(frame, 'Widget', 'SetVisibility', InVisibility=self.invisible)
            self._call(label, 'TextLayoutWidget', 'SetJustification', InJustification=1)
        else:
            self._place(label, x, y, width, height)
        # HitTestInvisible controls input without applying the disabled tint.
        self._call(label, 'Widget', 'SetIsEnabled', bInIsEnabled=True)
        self._call(label, 'Widget', 'SetVisibility', InVisibility=self.invisible)
        return label

    def _flush_layout(self):
        from . import _ui_batch
        if self._layout_queue is None:
            return
        queued, self._layout_queue = self._layout_queue, None
        # Bounded groups share one game-thread dispatch. A failed group stops
        # construction; no remaining group, root assignment or replay follows.
        for start in range(0, len(queued), _ui_batch.LIMIT):
            prepared = [self._planner.prepare(obj, self._function(owner, name), **args)
                        for obj, owner, name, args in queued[start:start + _ui_batch.LIMIT]]
            self._mutate(_ui_batch.invoke_setters, self.scope, prepared)

    def _root(self):
        if self._selected_results:
            # Read the owned tree and expected root identities freshly. Their
            # class/outer closures are sufficient to decode RootWidget; unrelated
            # objects do not need enumeration. Missing/changed references fail.
            objects = (self.tree,) if self.canvas is None else (self.tree, self.canvas)
            catalog = capture_selected(self.scope.pid,
                tuple((obj.index, obj.serial, obj.address) for obj in objects))
        else:
            catalog = capture()
        return read_values(catalog, catalog.resolve(self.tree)).values[
            self._class('WidgetTree').index, 'RootWidget']

    def build(self):
        if self.state != 'new':
            raise RuntimeError('Construct each panel once; close it before making another')
        self.state = 'building'
        started = time.perf_counter()
        log = logging.getLogger(__name__)
        log.info('Building owned native menu panel with %d reusable controls', self.count)
        self.catalog = capture_matching(self.scope.pid, names=(
            'Widget', 'UserWidget', 'CommonActivatableWidget', 'WidgetTree',
            'CanvasPanel', 'CanvasPanelSlot', 'Button', 'TextBlock', 'Border',
            'CommonTextBlock', 'WBP_BaseButton_C', 'CTS_B1_SmallLine_Outline_C', 'SetStyle',
            'Overlay', 'OverlaySlot', 'TextLayoutWidget', 'AddChildToOverlay',
            'SetHorizontalAlignment', 'SetVerticalAlignment', 'SetJustification',
            'EHorizontalAlignment', 'EVerticalAlignment', 'ETextJustify',
            'WidgetBlueprintLibrary', 'GameplayStatics',
            'Default__WidgetBlueprintLibrary', 'Default__GameplayStatics',
            'ESlateVisibility', 'Vector2D', 'LinearColor', 'Margin', 'Anchors',
            'Create', 'SpawnObject', 'AddChildToCanvas', 'SetPosition', 'SetSize',
            'SetAnchors', 'SetIsEnabled', 'SetVisibility', 'SetBackgroundColor', 'SetBrushColor',
            'SetText', 'AddToViewport', 'IsInViewport', 'ActivateWidget',
            'IsActivated', 'SetUserFocus', 'HasKeyboardFocus', 'HasUserFocus',
            'DeactivateWidget', 'RemoveFromParent', 'SetFocusToGameViewport',
            'SetInputMode_UIOnlyEx','SetInputMode_GameOnly','EMouseLockMode') + self.EXTRA_NAMES,
            classes=('PlayerController', 'GameEngine')) if self._selected_results else capture()
        if self.catalog.pid != self.scope.pid:
            raise ValueError('Widget catalog belongs to another process')
        self.player = self._one(o for o in self.catalog.select('PlayerController')
                                if not o.object_flags & 0x10)
        if self._selected_results:
            # Exact-name discovery also finds transient instances (notably an
            # old panel's WidgetTree). Do not merge those unowned registry slots
            # with future retained creation results after GC recycles them.
            descriptors = {'Function', 'ScriptStruct', 'Enum'}
            engines = {o.index for o in self.catalog.select('GameEngine')}
            self.catalog = self.catalog.subset(o for o in self.catalog.objects
                if o.index in self.catalog.classes or o.class_name in descriptors
                or o.name in ('Default__GameplayStatics', 'Default__WidgetBlueprintLibrary')
                or o.index == self.player.index or o.index in engines)
        enum = self.catalog.find_path('/Script/UMG.ESlateVisibility', 'Enum')
        descriptor = describe_enums(self.catalog, [enum])[enum.index]
        def visibility(name):
            member = self._one(m for m in descriptor.members
                               if m.name.rsplit('::', 1)[-1] == name)
            return descriptor.value(member.name)
        self.invisible = visibility('HitTestInvisible')
        self.visible = visibility('Visible')
        self.collapsed = visibility('Collapsed')
        if self._cached_construction:
            self._planner = self.scope.invocation_planner(
                selected_results=self._selected_results, catalog=self.catalog)
            from . import _ui_batch
            if _ui_batch.layout_available(self.scope._session):
                self._layout_queue = []
        self.timings['discovery_ms'] = (time.perf_counter() - started) * 1000
        self.widget = self._construction_call(
            self._default('WidgetBlueprintLibrary'), self._function('WidgetBlueprintLibrary', 'Create'),
            WorldContextObject=self.player, WidgetType=self._class('CommonActivatableWidget'),
            OwningPlayer=self.player).return_value
        if self._selected_results:
            self.tree, current = read_object_reference(self._planner._catalog,
                self.widget, self._class('UserWidget'), 'WidgetTree')
        else:
            current = capture()
            self.tree = read_values(current, current.resolve(self.widget)).values[
                self._class('UserWidget').index, 'WidgetTree']
        if self._planner is not None:
            # Create also initializes WidgetTree, which is a child and therefore
            # outside the returned widget's outer/class dependency closure.
            # Adopt the verified property-reference closure (or full observation).
            self._planner.refresh_from(current)
        if self.tree is None or self.tree.outer_index != self.widget.index or self._root() is not None:
            raise RuntimeError('New widget does not have the expected empty owned tree')
        self.canvas = self._spawn('CanvasPanel')
        # A native, hit-testable backdrop prevents clicks reaching the paused
        # game's controls through gaps in the SDK menu. It shares tree cleanup.
        backdrop = self._spawn('Border')
        backdrop_slot = self._place(backdrop, 0, 0, 0, 0)
        self._call(backdrop_slot, 'CanvasPanelSlot', 'SetAnchors',
            InAnchors={'Minimum': {'X': 0., 'Y': 0.}, 'Maximum': {'X': 1., 'Y': 1.}})
        self._call(backdrop, 'Border', 'SetBrushColor',
            InBrushColor={'R': .015, 'G': .02, 'B': .03, 'A': .55})
        self._build_contents()
        self._flush_layout()
        self._mutate(self.scope.assign_object, self.tree, self._class('WidgetTree'),
            'RootWidget', self.canvas, expected=None, allow_mutation=True,
            catalog=self._planner._catalog if self._planner is not None else None)
        self.assigned = True
        root = self._root()
        if root is None or (root.index, root.serial) != (self.canvas.index, self.canvas.serial):
            raise RuntimeError('Widget root assignment readback failed')
        self.state = 'built'
        self.timings['total_ms'] = (time.perf_counter() - started) * 1000
        log.info('Native menu build timings: %s', self.timings)
        log.info('Owned native menu tree built; awaiting paint and attachment')
        return self

    def _build_contents(self):
        self.title = self._label(90, 65, 1700, 70)
        self.detail = self._label(1120, 155, 760, 760)
        for index in range(self.count):
            art = self._construction_call(self._default('WidgetBlueprintLibrary'),
                self._function('WidgetBlueprintLibrary', 'Create'),
                WorldContextObject=self.player, WidgetType=self._class('WBP_BaseButton_C'),
                OwningPlayer=self.player).return_value
            self._place(art, 80, 155 + index * 64, 980, 56)
            self._call(art, 'Widget', 'SetVisibility', InVisibility=self.invisible)
            self.button_art.append(art)
            button = self._spawn('Button')
            self._place(button, 80, 155 + index * 64, 980, 56)
            self.buttons.append(button)
            self._call(button, 'Widget', 'SetIsEnabled', bInIsEnabled=True)
            self._call(button, 'Button', 'SetBackgroundColor',
                InBackgroundColor={'R':1.,'G':1.,'B':1.,'A':0.})
            self.labels.append(self._label(80, 155 + index * 64, 980, 56, centered=True))
            self._visible[index] = True
            self._enabled[index] = True

    def enable_cached_planning(self):
        """Opt in after construction; all rendered widget identities now exist.

        This changes repaint planning only. Native validation and the scope's
        retained-result ownership remain unchanged. No failed-call fallback.
        """
        if self.state != 'built' or self.uncertain:
            raise RuntimeError('Enable cached planning after a successful build, before opening')
        if self._planner is None:
            self._planner = self.scope.invocation_planner()

    def _render_call(self, obj, owner, name, **arguments):
        function = self._function(owner, name)
        if self._planner is None:
            result = self._mutate(self.scope.invoke_retained, obj, function, **arguments)
        else:
            # Planning failure has not dispatched anything. Dispatch uncertainty
            # still latches exactly as on the ordinary path.
            prepared = self._planner.prepare(obj, function, **arguments)
            if self._paint_queue is not None:
                self._paint_queue.append(prepared)
                return
            result = self._mutate(prepared.invoke)
        with result:
            pass

    def set_text(self, label, text):
        if self.state not in ('built', 'open'):
            raise RuntimeError('Panel is not available for rendering')
        if label not in (self.title, self.detail, *self.labels):
            raise ValueError('Text label does not belong to this panel')
        if self._text.get(label.index) == text:
            return
        self._render_call(label, 'TextBlock', 'SetText', InText=text)
        self._text[label.index] = text

    def set_enabled(self, index, enabled):
        if self.state not in ('built', 'open'):
            raise RuntimeError('Panel is not available for rendering')
        if type(index) is not int or not 0 <= index < self.count or type(enabled) is not bool:
            raise ValueError('Invalid control state')
        if self._enabled.get(index) != enabled:
            self._render_call(self.buttons[index], 'Widget', 'SetIsEnabled', bInIsEnabled=enabled)
            if self.button_art:
                self._render_call(self.button_art[index], 'Widget', 'SetIsEnabled', bInIsEnabled=enabled)
            self._enabled[index] = enabled

    def open(self):
        if self.state != 'built':
            raise RuntimeError('Build and paint the panel before opening it')
        from .menu import MenuError
        try:
            self.menu = self._mutate(self.scope.prepare_menu, self.widget, self.buttons[0], self.player,
                catalog=self._planner._catalog if self._planner is not None else None)
        except MenuError as error:
            # Invalid preparation never attaches or changes focus. Only this
            # acknowledged rejection is safe to dispose; uncertainty stays latched.
            code = error.native_error
            if error.outcome == 'returned' and (code in (811, 901, 902) or
                    isinstance(code, int) and (910 <= code <= 919 or 10000 <= code < 20000)):
                self.uncertain = False
            raise
        try:
            if not self._mutate(self.menu.attach) or not self._mutate(self.menu.focus):
                raise RuntimeError('Native panel attachment/focus deferred; close the panel')
        except MenuError as error:
            # A returned focus rejection has a known native owner. Detach it
            # immediately; never leave an unfocused overlay trapping the user.
            # Unknown/quarantined outcomes retain their existing no-retry latch.
            if error.outcome == 'returned' and error.native_error == 811:
                self.uncertain = False
                if self._mutate(self.menu.close):
                    self.menu = None
            raise
        self.state = 'open'

    def prime_menu_plan(self):
        """Prepare copied call descriptions, without focus/viewport ownership."""
        if self.state != 'built' or self.uncertain or self._planner is None:
            raise RuntimeError('Prime only a built owned panel')
        from .menu import prepare
        prepare(self.scope._session, self.widget, self.buttons[0], self.player,
                self.scope._leases, catalog=self._planner._catalog, _plan_only=True)

    def set_visible(self, index, visible):
        if self.state not in ('built', 'open'):
            raise RuntimeError('Panel is not available for rendering')
        if type(index) is not int or not 0 <= index < self.count or type(visible) is not bool:
            raise ValueError('Invalid control visibility')
        if self._visible.get(index) == visible:
            return
        for obj, value in ((self.buttons[index], self.visible if visible else self.collapsed),
                           (self.labels[index], self.invisible if visible else self.collapsed)):
            self._render_call(obj, 'Widget', 'SetVisibility', InVisibility=value)
        if self.button_art:
            self._render_call(self.button_art[index], 'Widget', 'SetVisibility',
                              InVisibility=self.invisible if visible else self.collapsed)
        self._visible[index] = visible

    def hide(self):
        """Detach input/viewport ownership, retaining the owned UObject tree.

        Reopening acquires fresh native focus and Slate references. None of the
        previous native menu's callbacks or SWidget addresses are reused.
        Full scope teardown remains close(), including on mod/session shutdown.
        """
        if self.state == 'built':
            return True
        if self.state != 'open' or self.uncertain:
            raise RuntimeError('Only a known open panel can be hidden')
        if not self.menu.close():
            return False
        self.menu = None
        self.state = 'built'
        return True

    def close(self):
        if self.state == 'closed':
            return True
        # Native ownership must finish before tree changes or leases are released.
        if self.menu is not None and not self.menu.close():
            return False
        if self.uncertain:
            raise RuntimeError('Panel tree outcome unknown; preserve owner for session cleanup')
        if self.assigned:
            self._mutate(self.scope.assign_object, self.tree, self._class('WidgetTree'),
                'RootWidget', None, expected=self.canvas, allow_mutation=True,
                catalog=self._planner._catalog if self._planner is not None else None)
            self.assigned = False
            if self._root() is not None:
                raise RuntimeError('Panel root was not restored')
        if self._planner is not None and self.children and not self._selected_results:
            # Native input is detached and the root readback has succeeded.
            # All children remain leased. Refresh once for teardown; native
            # identity/schema gates still run for every removal. A failed
            # refresh does not dispatch or fall back to another mutation path.
            self._planner.refresh()
        # Selected-result panels already retain every child and its verified
        # planning closure. Native dispatch revalidates the identity/schema on
        # each removal. Enumerating the entire world here adds seconds without
        # granting any additional dispatch authority.
        while self.children:
            child = self.children[-1]
            if self._planner is not None:
                self._render_call(child, 'Widget', 'RemoveFromParent')
            else:
                self._call(child, 'Widget', 'RemoveFromParent')
            self.children.pop()
        if self._planner is not None:
            self._planner.close()
            self._planner = None
        self.scope.close()
        self._text.clear()
        self._enabled.clear()
        self._visible.clear()
        self._functions.clear()
        self._defaults.clear()
        self.state = 'closed'
        return True
