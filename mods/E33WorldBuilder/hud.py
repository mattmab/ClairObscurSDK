"""Noninteractive viewport overlay: owns widgets, never acquires input focus."""
from expedition33.widgets import OwnedMenuPanel
from expedition33.catalog import capture_matching
from expedition33.values import read_object_reference
from expedition33.enums import describe_enums


class BuilderHUD(OwnedMenuPanel):
    def __init__(self, session):
        super().__init__(session, controls=1, cached_construction=True, selected_results=True)
        self.lines = []
        self.slots = []
        self.crosshair = []

    def build(self):
        self.state = 'building'
        self.catalog = capture_matching(self.scope.pid, names=(
            'UserWidget','CommonActivatableWidget','WidgetTree','CanvasPanel','CanvasPanelSlot',
            'Border','Widget','TextBlock','CommonTextBlock','CTS_B1_SmallLine_Outline_C',
            'TextLayoutWidget','SetStyle','SetJustification','WidgetBlueprintLibrary','GameplayStatics',
            'Default__WidgetBlueprintLibrary','Default__GameplayStatics','ESlateVisibility',
            'ETextJustify','Vector2D','LinearColor','Anchors','Create','SpawnObject','AddChildToCanvas','SetPosition',
            'SetSize','SetAnchors','SetIsEnabled','SetVisibility','SetBrushColor','SetText',
            'AddToViewport','RemoveFromParent'), classes=('PlayerController',))
        self.player = self._one(o for o in self.catalog.select('PlayerController') if not o.object_flags & 0x30)
        descriptors = {'Function','ScriptStruct','Enum'}
        self.catalog = self.catalog.subset(o for o in self.catalog.objects if o.index in self.catalog.classes
            or o.class_name in descriptors or o.name in ('Default__GameplayStatics','Default__WidgetBlueprintLibrary')
            or o.index == self.player.index)
        enum = self.catalog.find_path('/Script/UMG.ESlateVisibility','Enum')
        descriptor = describe_enums(self.catalog,[enum])[enum.index]
        self.invisible = descriptor.value(next(m.name for m in descriptor.members if m.name.endswith('::HitTestInvisible')))
        self.collapsed = descriptor.value(next(m.name for m in descriptor.members if m.name.endswith('::Collapsed')))
        self._planner = self.scope.invocation_planner(selected_results=True,catalog=self.catalog)
        self.widget = self._construction_call(self._default('WidgetBlueprintLibrary'),
            self._function('WidgetBlueprintLibrary','Create'), WorldContextObject=self.player,
            WidgetType=self._class('CommonActivatableWidget'), OwningPlayer=self.player).return_value
        self.tree,current = read_object_reference(self._planner._catalog,self.widget,self._class('UserWidget'),'WidgetTree')
        self._planner.refresh_from(current)
        if self.tree is None or self._root() is not None:
            raise RuntimeError('Expected an empty owned HUD tree')
        self.canvas = self._spawn('CanvasPanel')
        for i in range(6):
            line = self._spawn('Border')
            slot = self._place(line, -8 if i==4 else -1, -1 if i==4 else -8, 16 if i==4 else 2, 2 if i==4 else 16)
            self._call(line,'Border','SetBrushColor',InBrushColor={'R':1.,'G':1.,'B':1.,'A':.95})
            self._call(line,'Widget','SetVisibility',InVisibility=self.invisible if i>=4 else self.collapsed)
            if i>=4:
                self._call(slot,'CanvasPanelSlot','SetAnchors',InAnchors={'Minimum':{'X':.5,'Y':.5},'Maximum':{'X':.5,'Y':.5}})
                self.crosshair.append(line)
            else:
                self.lines.append(line);self.slots.append(slot)
        self.title = self._label(-500,30,1000,60)
        self.detail = self.title
        # The most recently placed child is the label; center its slot using
        # the reflected PanelSlot reference instead of fixed screen dimensions.
        slot,current = read_object_reference(self._planner._catalog,self.title,self._class('Widget'),'Slot')
        self._planner.refresh_from(current)
        self._call(slot,'CanvasPanelSlot','SetAnchors',InAnchors={'Minimum':{'X':.5,'Y':0.},'Maximum':{'X':.5,'Y':0.}})
        self._call(self.title,'TextLayoutWidget','SetJustification',InJustification=1)
        self._call(self.widget,'Widget','SetVisibility',InVisibility=self.invisible)
        self._mutate(self.scope.assign_object,self.tree,self._class('WidgetTree'),'RootWidget',self.canvas,
                     expected=None,allow_mutation=True,catalog=self._planner._catalog)
        self.assigned=True
        self.state='built'
        self.set_text(self.title,'WORLD BUILDER | Aim at a prop')
        self._render_call(self.widget,'UserWidget','AddToViewport',ZOrder=10000)
        return self

    def close(self):
        if self.widget is not None and self.state != 'closed':
            self._render_call(self.widget,'Widget','RemoveFromParent')
        return super().close()

