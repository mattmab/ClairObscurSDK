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
    def __init__(self, session, *, controls=12):
        session._check()
        if not session.supports_multi_controls:
            raise ValueError('Owned menu panels require v17 multi-control support')
        if type(controls) is not int or not 1 <= controls <= 16:
            raise ValueError('A panel requires between1 and16 controls')
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

    @staticmethod
    def _one(rows):
        rows = tuple(rows)
        if len(rows) != 1:
            raise ValueError('Expected one target-build widget identity')
        return rows[0]

    def _function(self, owner, name):
        return self._one(o for o in self.catalog.objects
            if o.outer_index == self._class(owner).index and o.name == name)

    def _class(self, name):
        return self.catalog.by_index[self.catalog.find_class(name).index]

    def _default(self, name):
        return self._one(o for o in self.catalog.objects
            if o.class_index == self._class(name).index and o.name == 'Default__' + name)

    def _mutate(self, method, *args, **kwargs):
        if self.uncertain:
            raise RuntimeError('Widget mutation outcome unknown; no retry is permitted')
        self.uncertain = True
        result = method(*args, **kwargs)
        self.uncertain = False
        return result

    def _call(self, obj, owner, name, **args):
        return self._mutate(self.scope.invoke, obj, self._function(owner, name), **args)

    def _spawn(self, name):
        return self._mutate(self.scope.invoke_retained,
            self._default('GameplayStatics'), self._function('GameplayStatics', 'SpawnObject'),
            ObjectClass=self._class(name), Outer=self.tree).return_value

    def _place(self, child, x, y, width, height):
        slot = self._mutate(self.scope.invoke_retained, self.canvas,
            self._function('CanvasPanel', 'AddChildToCanvas'), Content=child).return_value
        self.children.append(child)
        self._call(slot, 'CanvasPanelSlot', 'SetPosition', InPosition={'X':float(x),'Y':float(y)})
        self._call(slot, 'CanvasPanelSlot', 'SetSize', InSize={'X':float(width),'Y':float(height)})
        self._call(slot, 'CanvasPanelSlot', 'SetAnchors',
            InAnchors={'Minimum':{'X':0.0,'Y':0.0},'Maximum':{'X':0.0,'Y':0.0}})

    def _label(self, x, y, width, height):
        label = self._spawn('TextBlock')
        self._place(label, x, y, width, height)
        self._call(label, 'Widget', 'SetIsEnabled', bInIsEnabled=False)
        with self._mutate(self.scope.invoke_retained, label,
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
        member = self._one(m for m in descriptor.members
                           if m.name.rsplit('::', 1)[-1] == 'HitTestInvisible')
        self.invisible = descriptor.value(member.name)
        self.widget = self._mutate(self.scope.invoke_retained,
            self._default('WidgetBlueprintLibrary'), self._function('WidgetBlueprintLibrary', 'Create'),
            WorldContextObject=self.player, WidgetType=self._class('CommonActivatableWidget'),
            OwningPlayer=self.player).return_value
        current = capture()
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

    def set_text(self, label, text):
        if self.state not in ('built', 'open'):
            raise RuntimeError('Panel is not available for rendering')
        if label not in (self.title, self.detail, *self.labels):
            raise ValueError('Text label does not belong to this panel')
        if self._text.get(label.index) == text:
            return
        with self._mutate(self.scope.invoke_retained, label,
                self._function('TextBlock', 'SetText'), InText=text):
            pass
        self._text[label.index] = text

    def set_enabled(self, index, enabled):
        if self.state not in ('built', 'open'):
            raise RuntimeError('Panel is not available for rendering')
        if type(index) is not int or not 0 <= index < self.count or type(enabled) is not bool:
            raise ValueError('Invalid control state')
        if self._enabled.get(index) != enabled:
            self._call(self.buttons[index], 'Widget', 'SetIsEnabled', bInIsEnabled=enabled)
            self._enabled[index] = enabled

    def open(self):
        if self.state != 'built':
            raise RuntimeError('Build and paint the panel before opening it')
        self.menu = self._mutate(self.scope.prepare_menu, self.widget, self.buttons[0], self.player)
        if not self._mutate(self.menu.attach) or not self._mutate(self.menu.focus):
            raise RuntimeError('Native panel attachment/focus deferred; close the panel')
        self.state = 'open'

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
        while self.children:
            child = self.children[-1]
            self._call(child, 'Widget', 'RemoveFromParent')
            self.children.pop()
        self.scope.close()
        self._text.clear()
        self._enabled.clear()
        self.state = 'closed'
        return True
