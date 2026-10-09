"""Owned native UMG panel built from the verified base-widget paths.

Experimental v17 renderer infrastructure. No game assets, stock offsets, input
mode resets, research-script imports or independent controller are used here.
Construction is explicit so callers retain the owner even if a mutation fails.
"""
import logging

from .catalog import capture
from .enums import describe_enums
from .values import read_values
from ._scope import SessionScope


class OwnedMenuPanel:
    def __init__(self, session, *, controls=12, cached_construction=False, selected_results=False):
        session._check()
        if not session.supports_multi_controls:
            raise ValueError('Owned menu panels require v17 multi-control support')
        if type(controls) is not int or not 1 <= controls <= 16:
            raise ValueError('A panel requires between1 and16 controls')
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
        self.assigned = False
        self.uncertain = False
        self._text = {}
        self._enabled = {}
        self._visible = {}
        self._planner = None

    @staticmethod
    def _one(rows):
        rows = tuple(rows)
        if len(rows) != 1:
            raise ValueError('Expected one target-build widget identity')
        return rows[0]

    def _function(self, owner, name):
        owner_index = self._class(owner).index
        return self._one(o for o in self.catalog.objects
            if o.outer_index == owner_index and o.name == name)

    def _class(self, name):
        return self.catalog.by_index[self.catalog.find_class(name).index]

    def _default(self, name):
        class_index = self._class(name).index
        return self._one(o for o in self.catalog.objects
            if o.class_index == class_index and o.name == 'Default__' + name)

    def _mutate(self, method, *args, **kwargs):
        if self.uncertain:
            raise RuntimeError('Widget mutation outcome unknown; no retry is permitted')
        self.uncertain = True
        result = method(*args, **kwargs)
        self.uncertain = False
        return result

    def _call(self, obj, owner, name, **args):
        if self.state == 'building' and self._planner is not None:
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

    def _label(self, x, y, width, height):
        label = self._spawn('TextBlock')
        self._place(label, x, y, width, height)
        # HitTestInvisible controls input without applying the disabled tint.
        self._call(label, 'Widget', 'SetIsEnabled', bInIsEnabled=True)
        with self._construction_call(label,
                self._function('Widget', 'SetVisibility'), InVisibility=self.invisible):
            pass
        return label

    def _root(self):
        catalog = capture()
        return read_values(catalog, catalog.resolve(self.tree)).values[
            self._class('WidgetTree').index, 'RootWidget']

    def build(self):
        if self.state != 'new':
            raise RuntimeError('Construct each panel once; close it before making another')
        self.state = 'building'
        log = logging.getLogger(__name__)
        log.info('Building owned native menu panel with %d reusable controls', self.count)
        self.catalog = capture()
        if self.catalog.pid != self.scope.pid:
            raise ValueError('Widget catalog belongs to another process')
        self.player = self._one(o for o in self.catalog.select('PlayerController')
                                if not o.object_flags & 0x10)
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
            self._planner = self.scope.invocation_planner(selected_results=self._selected_results)
        self.widget = self._construction_call(
            self._default('WidgetBlueprintLibrary'), self._function('WidgetBlueprintLibrary', 'Create'),
            WorldContextObject=self.player, WidgetType=self._class('CommonActivatableWidget'),
            OwningPlayer=self.player).return_value
        current = capture()
        if self._planner is not None:
            # Create also initializes WidgetTree, which is a child and therefore
            # outside the returned widget's outer/class dependency closure.
            # Adopt the full observation already needed for the property read.
            self._planner.refresh_from(current)
        self.tree = read_values(current, current.resolve(self.widget)).values[
            self._class('UserWidget').index, 'WidgetTree']
        if self.tree is None or self.tree.outer_index != self.widget.index or self._root() is not None:
            raise RuntimeError('New widget does not have the expected empty owned tree')
        self.canvas = self._spawn('CanvasPanel')
        self.title = self._label(90, 65, 1700, 70)
        self.detail = self._label(1120, 155, 760, 760)
        for index in range(self.count):
            button = self._spawn('Button')
            self._place(button, 80, 155 + index * 64, 980, 56)
            self.buttons.append(button)
            self._call(button, 'Widget', 'SetIsEnabled', bInIsEnabled=True)
            self._call(button, 'Button', 'SetBackgroundColor',
                InBackgroundColor={'R':0.08,'G':0.12,'B':0.18,'A':1.0})
            self.labels.append(self._label(100, 163 + index * 64, 940, 46))
            self._visible[index] = True
            self._enabled[index] = True
            log.info('Native menu construction: control %d/%d retained', index + 1, self.count)
        self._mutate(self.scope.assign_object, self.tree, self._class('WidgetTree'),
            'RootWidget', self.canvas, expected=None, allow_mutation=True)
        self.assigned = True
        root = self._root()
        if root is None or (root.index, root.serial) != (self.canvas.index, self.canvas.serial):
            raise RuntimeError('Widget root assignment readback failed')
        self.state = 'built'
        log.info('Owned native menu tree built; awaiting paint and attachment')
        return self

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
            self._enabled[index] = enabled

    def open(self):
        if self.state != 'built':
            raise RuntimeError('Build and paint the panel before opening it')
        self.menu = self._mutate(self.scope.prepare_menu, self.widget, self.buttons[0], self.player)
        if not self._mutate(self.menu.attach) or not self._mutate(self.menu.focus):
            raise RuntimeError('Native panel attachment/focus deferred; close the panel')
        self.state = 'open'

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
        self._visible[index] = visible

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
                'RootWidget', None, expected=self.canvas, allow_mutation=True)
            self.assigned = False
            if self._root() is not None:
                raise RuntimeError('Panel root was not restored')
        if self._planner is not None and self.children:
            # Native input is detached and the root readback has succeeded.
            # All children remain leased. Refresh once for teardown; native
            # identity/schema gates still run for every removal. A failed
            # refresh does not dispatch or fall back to another mutation path.
            self._planner.refresh()
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
        self.state = 'closed'
        return True
