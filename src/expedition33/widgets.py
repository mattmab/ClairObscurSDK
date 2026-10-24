"""Owned native UMG panel built from the verified base-widget paths.

Experimental v17 renderer infrastructure. No game assets, stock offsets, input
mode resets, research-script imports or independent controller are used here.
Construction is explicit so callers retain the owner even if a mutation fails.
"""
import logging
import time
from contextlib import contextmanager
from ._menu_latency import MenuLatency, measure_method

from .catalog import capture, capture_selected, capture_matching
from .enums import describe_enums
from .values import read_values, read_object_reference
from ._scope import SessionScope
from .invocation import InvocationError


_WIDGET_DEFINITIONS = frozenset((
    'Widget', 'UserWidget', 'CommonActivatableWidget', 'WidgetTree',
    'CanvasPanel', 'CanvasPanelSlot', 'Button', 'TextBlock', 'Border',
    'CommonTextBlock', 'WBP_BaseButton_C', 'CTS_B1_SmallLine_Outline_C',
    'Overlay', 'OverlaySlot', 'TextLayoutWidget', 'WidgetBlueprintLibrary',
    'GameplayStatics', 'EditableText', 'ScrollBox', 'SizeBox', 'PanelWidget',
    'ContentWidget', 'Slider',
))


def widget_definition_names(names):
    # A CDO's closure includes its class. Bare names such as WidgetTree also
    # match every Blueprint instance, exceeding the reader's 1024-hit cap.
    return tuple(dict.fromkeys('Default__' + name if name in _WIDGET_DEFINITIONS
                               else name for name in names))


class OwnedMenuPanel:
    EXTRA_NAMES = ()
    BATCH_CONSTRUCTION = False

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
        self.latency = MenuLatency()
        self._construction = None

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
            self.latency.count('paint.queued_setters',len(self._paint_queue))
            for start in range(0, len(self._paint_queue), _ui_batch.LIMIT):
                self.latency.count('paint.batch_dispatches')
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

    @measure_method('widget.mutation')
    def _mutate(self, method, *args, **kwargs):
        if self.uncertain:
            raise RuntimeError('Widget mutation outcome unknown; no retry is permitted')
        self.uncertain = True
        self.latency.count('mutation.'+getattr(method,'__name__','callable'))
        try:
            result = method(*args, **kwargs)
        except InvocationError as error:
            # A correlated rejection proves this operation did not execute.
            # Earlier acknowledged operations stand; do not replay this call.
            if error.outcome == 'not_dispatched':
                self.uncertain = False
            raise
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
        if self._construction is not None:
            return self._construction.record(obj, function, arguments)
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
        if self._construction is not None:
            construction, self._construction = self._construction, None
            construction.flush(self)
        if self._layout_queue is None:
            return
        queued, self._layout_queue = self._layout_queue, None
        # Bounded groups share one game-thread dispatch. A failed group stops
        # construction; no remaining group, root assignment or replay follows.
        for start in range(0, len(queued), _ui_batch.LIMIT):
            prepared = [self._planner.prepare(obj, self._function(owner, name), **args)
                        for obj, owner, name, args in queued[start:start + _ui_batch.LIMIT]]
            self._mutate(_ui_batch.invoke_setters, self.scope, prepared)
            from .loading_preparation import service_loading_io
            service_loading_io(getattr(self.scope,'_session',None))

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

    @measure_method('widget.build')
    def build(self):
        if self.state != 'new':
            raise RuntimeError('Construct each panel once; close it before making another')
        self.state = 'building'
        started = time.perf_counter()
        log = logging.getLogger(__name__)
        log.info('Building owned native menu panel with %d reusable controls', self.count)
        def discover_metadata():
            catalog = capture_matching(self.scope.pid, names=widget_definition_names((
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
                'SetInputMode_UIOnlyEx','SetInputMode_GameOnly','EMouseLockMode') + self.EXTRA_NAMES),
                classes=('GameEngine',)) if self._selected_results else capture()
            if catalog.pid != self.scope.pid:
                raise ValueError('Widget catalog belongs to another process')
            if self._selected_results:
                from .cinematics.original_game_action import controller_context
                current = controller_context(self.scope)
                observed = capture_selected(self.scope.pid, (current['controller'][1:],))
                catalog = catalog.with_observations(observed)
                self.player = catalog.by_index[current['controller'][1]]
            else:
                self.player = self._one(o for o in catalog.select('PlayerController')
                                        if not o.object_flags & 0x10)
            if self._selected_results:
                # Exact-name discovery also finds transient instances (notably an
                # old panel's WidgetTree). Do not merge those unowned registry slots
                # with future retained creation results after GC recycles them.
                descriptors = {'Function', 'ScriptStruct', 'Enum'}
                engines = {o.index for o in catalog.select('GameEngine')}
                catalog = catalog.subset(o for o in catalog.objects
                    if o.index in catalog.classes or o.class_name in descriptors
                    or o.name in ('Default__GameplayStatics', 'Default__WidgetBlueprintLibrary')
                    or o.index == self.player.index or o.index in engines)
            return catalog
        from ._metadata_stabilization import available,prepare_discovery
        self._metadata_stable_ui=False
        if self._selected_results and available(getattr(self.scope._session,'_transport',None)):
            self.catalog,uncovered=prepare_discovery(self.scope._session,discover_metadata)
            self.metadata_uncovered_count=len(uncovered);self._metadata_stable_ui=True
        else:self.catalog=discover_metadata()
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
            self._planner._require_stable_ui_identities=self._metadata_stable_ui
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
                self.widget, self._class('UserWidget'), 'WidgetTree', project=True)
        else:
            current = capture()
            self.tree = read_values(current, current.resolve(self.widget)).values[
                self._class('UserWidget').index, 'WidgetTree']
        from ._stable_lease import available as stable_tree_available, stabilize_owned_tree, rediscover_owned_tree
        if (self.tree is not None and self.tree.serial==0 and
                stable_tree_available(self.scope._session._transport)):
            stable_tree, _ = stabilize_owned_tree(self.scope, current, self.widget,
                self.tree, self._class('UserWidget'))
            # The old tree's serial changed intentionally. Discard its catalog;
            # never merge the replacement identity through with_observations.
            self.catalog,self.tree,current = rediscover_owned_tree(self.scope.pid,
                discover_metadata,self.widget,stable_tree,self._class('UserWidget').index)
            if self._planner is not None:
                self._planner.refresh_from(self.catalog)
        if self._planner is not None:
            # Create also initializes WidgetTree, which is a child and therefore
            # outside the returned widget's outer/class dependency closure.
            # Adopt the verified property-reference closure (or full observation).
            if self._selected_results:
                self._planner.adopt_observations(current)
            else:
                self._planner.refresh_from(current)
        if self.tree is None or self.tree.outer_index != self.widget.index or self._root() is not None:
            raise RuntimeError('New widget does not have the expected empty owned tree')
        from . import _ui_construction
        if (self.BATCH_CONSTRUCTION and self._selected_results and self._layout_queue is not None and
                _ui_construction.available(self.scope._session)):
            self._construction = _ui_construction.Construction()
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
        self._planner._require_stable_ui_identities=getattr(self,'_metadata_stable_ui',False)

    @measure_method('widget.render_plan')
    def _render_call(self, obj, owner, name, **arguments):
        self.latency.count('setter.'+owner+'.'+name)
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
            try:
                result = self._mutate(prepared.invoke)
            except InvocationError as error:
                if error.outcome == 'not_dispatched' and error.native_error == 202:
                    self._diagnose_rejected_identity(obj, function)
                raise
        with result:
            pass

    def _diagnose_rejected_identity(self, target, function):
        # Post-rejection observation only. Never retries a failed invocation,
        # changes its outcome, logs arguments, or grants dispatch authority.
        for role, obj in (('target', target), ('function', function)):
            identity = (obj.index, obj.serial, obj.address)
            try:
                observed = capture_selected(self.scope.pid, (identity,)).by_index[obj.index]
                logging.getLogger(__name__).error(
                    'UI rejection202 %s index=%d serial=%d address=%#x observed_flags=%#x',
                    role, obj.index, obj.serial, obj.address, observed.object_flags)
            except Exception as diagnostic_error:
                logging.getLogger(__name__).error(
                    'UI rejection202 %s index=%d serial=%d address=%#x observation_failed=%s',
                    role, obj.index, obj.serial, obj.address, type(diagnostic_error).__name__)

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

    @measure_method('widget.open_attach_focus')
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

    @measure_method('widget.prime_menu_plan')
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

    def retire_world(self, *, native_retirement_ack=False):
        """Release this SDK-owned hierarchy without old-world UI restoration."""
        if self.state=='closed':return 'ack'
        if self.uncertain:return 'unknown'
        if self.menu is not None:
            if not self.menu.retire_world():return 'pending'
        elif self.state=='open':
            # Noninteractive overlays have no native input owner. Only a
            # preceding native domain retirement ACK permits their detach.
            if not native_retirement_ack:return 'unknown'
            self._render_call(self.widget,'Widget','RemoveFromParent')
        if self._planner is not None:self._planner.close();self._planner=None
        self.scope.close()
        self.menu=None;self.assigned=False;self.children.clear()
        self.state='closed';return 'ack'

    def close(self):
        return self._close_tree(detach_children=True)

    def close_owned_tree(self):
        """Release a wholly owned detached tree without removing each child.

        Input ownership is closed first and RootWidget is cleared/read back.
        Children reference only this owned tree; releasing its leases lets UE
        collect the hierarchy together. Never use this for borrowed widgets.
        """
        return self._close_tree(detach_children=False)

    def _close_tree(self, *, detach_children):
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
            if self._root() is not None:
                raise RuntimeError('Panel root was not restored')
            self.assigned = False
        if detach_children and self._planner is not None and self.children and not self._selected_results:
            # Native input is detached and the root readback has succeeded.
            # All children remain leased. Refresh once for teardown; native
            # identity/schema gates still run for every removal. A failed
            # refresh does not dispatch or fall back to another mutation path.
            self._planner.refresh()
        # Selected-result panels already retain every child and its verified
        # planning closure. Native dispatch revalidates the identity/schema on
        # each removal. Enumerating the entire world here adds seconds without
        # granting any additional dispatch authority.
        while detach_children and self.children:
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
        self.children.clear()
        self._text.clear()
        self._enabled.clear()
        self._visible.clear()
        self._functions.clear()
        self._defaults.clear()
        self.state = 'closed'
        return True
