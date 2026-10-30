"""Noninteractive viewport overlay: owns widgets, never acquires input focus."""
from expedition33.widgets import OwnedMenuPanel
from expedition33.catalog import capture_matching
from expedition33.values import read_object_reference
from expedition33.enums import describe_enums


class BuilderHUD(OwnedMenuPanel):
    def _place(self,child,*args):
        slot=super()._place(child,*args)
        if not hasattr(self,'_slots'):self._slots={}
        self._slots[child.index]=slot
        return slot

    def __init__(self, session, help_minimized=False):
        super().__init__(session, controls=1, cached_construction=True, selected_results=True)
        self.help_minimized = help_minimized
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
            'SetRenderScale','SetRenderTransformPivot','SetSize','SetAnchors','SetIsEnabled','SetVisibility','SetBrushColor','SetText',
            'AddToViewport','RemoveFromParent','SetRenderOpacity'), classes=('PlayerController',))
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
        self._layout_queue=[]
        self.widget = self._construction_call(self._default('WidgetBlueprintLibrary'),
            self._function('WidgetBlueprintLibrary','Create'), WorldContextObject=self.player,
            WidgetType=self._class('CommonActivatableWidget'), OwningPlayer=self.player).return_value
        self.tree,current = read_object_reference(self._planner._catalog,self.widget,self._class('UserWidget'),'WidgetTree')
        self._planner.refresh_from(current)
        if self.tree is None or self._root() is not None:
            raise RuntimeError('Expected an empty owned HUD tree')
        from expedition33 import _ui_construction
        if _ui_construction.available(self.scope._session):self._construction=_ui_construction.Construction()
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
        slot=self._slots[self.title.index]
        self._call(slot,'CanvasPanelSlot','SetAnchors',InAnchors={'Minimum':{'X':.5,'Y':0.},'Maximum':{'X':.5,'Y':0.}})
        self._call(self.title,'TextLayoutWidget','SetJustification',InJustification=1)
        self.selection_label=self._label(-490,110,760,100)
        self.controls_label=self._label(-490,190,760,690)
        self.labels.extend((self.selection_label,self.controls_label))
        for label in (self.selection_label,self.controls_label):
            slot=self._slots[label.index]
            self._call(slot,'CanvasPanelSlot','SetAnchors',InAnchors={'Minimum':{'X':1.,'Y':0.},'Maximum':{'X':1.,'Y':0.}})
            self._call(label,'Widget','SetRenderTransformPivot',Pivot={'X':0.,'Y':0.})
            self._call(label,'Widget','SetRenderScale',Scale={'X':.6,'Y':.6})
        self._call(self.widget,'Widget','SetVisibility',InVisibility=self.invisible)
        self._flush_layout()
        self._mutate(self.scope.assign_object,self.tree,self._class('WidgetTree'),'RootWidget',self.canvas,
                     expected=None,allow_mutation=True,catalog=self._planner._catalog)
        self.assigned=True
        self.state='built'
        self.set_text(self.title,'WORLD BUILDER | Aim at a prop')
        self.show_selection('None')
        self.show_help(self.help_minimized)
        return self

    def show_help(self, minimized):
        self.help_minimized = bool(minimized)
        self.set_text(self.controls_label, "(F1) Help" if minimized else
            'CONTROLS (F1: Minimize help)\n'
            'F7: Open / close menu | Esc: Back / close\n'
            'F8: Enter / leave builder camera | F6: Play from camera\n'
            'Hold Y/P/R + mouse: Yaw / Pitch / Roll\n'
            'Hold +/= or numpad +: Mouse up/down scales\n'
            'H: Hide / show builder HUD\n'
            'WASD: Fly | Mouse: Look\n'
            'Space / E: Up | Ctrl / Q: Down\n'
            'Shift: Fly faster\n'
            'LMB: Hold to move; release to place\n'
            'Click-copy mode: Click to copy / place\n'
            'F3 / F4: Region corners at camera\n'
            'Maps > Templates: Save / place structure\n'
            'F5: Live duplication panel\n'
            'F10: Copy selected prop into hand\n'
            'Delete: Delete current spawned selection\n'
            'Numpad 8 / 2: Move forward / back\n'
            'Numpad 6 / 4: Move right / left\n'
            'Numpad 9 / 3: Move up / down\n'
            'Numpad 7 / 1: Rotate yaw\n'
            'Alt: Precise movement\n'
            'Alt+Z: Undo | Alt+Y: Redo\n'
            'F9: Restore edits / clear spawned props\n'
            'Menu > Directional copies: Count / spacing')

    def show_selection(self,name,axis='',angle=0.):
        import textwrap
        detail=f'\nScale: {angle:.3f}x (this gesture)' if axis=='Scale' else f'\n{axis}: {angle:+.1f} degrees' if axis else ''
        self.set_text(self.selection_label,'CURRENT SELECTION\n'+textwrap.fill(name,width=42)+detail)

    def set_hidden(self, hidden):
        self._render_call(self.widget,'Widget','SetRenderOpacity',InOpacity=0. if hidden else 1.)

    def show_building(self, active):
        if active:
            self.set_text(self.controls_label, 'WORLD BUILDER\nBuilding Widgets...')
        else:
            self.show_help(self.help_minimized)

    def close(self):
        if self.widget is not None and self.state != 'closed':
            self._render_call(self.widget,'Widget','RemoveFromParent')
        return super().close()
