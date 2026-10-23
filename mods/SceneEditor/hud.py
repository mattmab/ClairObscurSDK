"""Noninteractive viewport overlay: owns widgets, never acquires input focus."""
from expedition33.widgets import OwnedMenuPanel
from expedition33.catalog import capture_matching, capture_selected
from expedition33.values import read_object_reference
from expedition33.enums import describe_enums


class SceneHUD(OwnedMenuPanel):
    def __init__(self, session, help_minimized=False):
        super().__init__(session, controls=1, cached_construction=True, selected_results=True)
        self.help_minimized = help_minimized
        self.lines = []
        self.slots = []
        self.crosshair = []
        self.photo_help=None;self.photo_help_opacity=None;self.photo_help_hidden=False;self.photo_help_compact=False;self.photo_help_transform=None

    def build(self):
        self.state = 'building'
        self.catalog = capture_matching(self.scope.pid, names=(
            'UserWidget','CommonActivatableWidget','WidgetTree','CanvasPanel','CanvasPanelSlot',
            'Border','Widget','TextBlock','CommonTextBlock','CTS_B1_SmallLine_Outline_C',
            'TextLayoutWidget','SetStyle','SetJustification','WidgetBlueprintLibrary','GameplayStatics',
            'Default__WidgetBlueprintLibrary','Default__GameplayStatics','ESlateVisibility',
            'ETextJustify','Vector2D','LinearColor','Anchors','Create','SpawnObject','AddChildToCanvas','SetPosition',
            'SetRenderScale','SetRenderTransformPivot','SetSize','SetAnchors','SetIsEnabled','SetVisibility','SetBrushColor','SetText',
            'AddToViewport','RemoveFromParent','SetRenderOpacity','SetRenderTranslation'), classes=('PlayerController',))
        from expedition33.cinematics.original_game_action import controller_context
        current = controller_context(self.scope)
        self.catalog = self.catalog.with_observations(capture_selected(self.scope.pid, (current['controller'][1:],)))
        self.player = self.catalog.by_index[current['controller'][1]]
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
        self.selection_label=self._label(-490,110,760,100)
        self.controls_label=self._label(-490,190,760,690)
        self.labels.extend((self.selection_label,self.controls_label))
        for label in (self.selection_label,self.controls_label):
            slot,current=read_object_reference(self._planner._catalog,label,self._class('Widget'),'Slot')
            self._planner.refresh_from(self._planner._catalog.with_observations(current))
            self._call(slot,'CanvasPanelSlot','SetAnchors',InAnchors={'Minimum':{'X':1.,'Y':0.},'Maximum':{'X':1.,'Y':0.}})
            self._call(label,'Widget','SetRenderTransformPivot',Pivot={'X':0.,'Y':0.})
            self._call(label,'Widget','SetRenderScale',Scale={'X':.6,'Y':.6})
        self._call(self.widget,'Widget','SetVisibility',InVisibility=self.invisible)
        self.aim_label=self._label(-14,-28,60,60)
        slot,current=read_object_reference(self._planner._catalog,self.aim_label,self._class('Widget'),'Slot');self._planner.refresh_from(current)
        self._call(slot,'CanvasPanelSlot','SetAnchors',InAnchors={'Minimum':{'X':.5,'Y':.5},'Maximum':{'X':.5,'Y':.5}})
        self.labels.append(self.aim_label)
        self._flush_layout()
        self._mutate(self.scope.assign_object,self.tree,self._class('WidgetTree'),'RootWidget',self.canvas,
                     expected=None,allow_mutation=True,catalog=self._planner._catalog)
        self.assigned=True
        self.state='built'
        self.set_text(self.title,'SCENE AUTHORING | Backspace: Show / hide Scene Editor UI | Home: cursor')
        self.set_text(self.aim_label,'')
        self.show_selection('None')
        self.show_help(self.help_minimized)
        return self

    def set_photo_help_hidden(self, hidden):
        if self.photo_help is None:
            from expedition33.catalog import capture_selected
            from expedition33.values import read_values
            current=capture_selected(self.scope.pid,((self.player.index,self.player.serial,self.player.address),))
            controller=current.by_index[self.player.index]
            if controller.class_name!='BP_PhotoModeController_C':return
            hud,current=read_object_reference(current,controller,current.by_index[controller.class_index],'PhotoModeHUD')
            if hud is None:raise RuntimeError('Photo mode HUD is unavailable')
            help_widget,current=read_object_reference(current,hud,current.by_index[hud.class_index],'WBP_PhotoModeInputsContainer')
            if help_widget is None:raise RuntimeError('Photo mode input help is unavailable')
            values=read_values(current,help_widget)
            self.photo_help_opacity=float(next(value for (_,name),value in values.values.items() if name=='RenderOpacity'))
            import struct
            runtime=self.photo_runtime
            data=runtime.registry.command(89,((88,runtime.registry.identity(help_widget)),))
            tx,ty,sx,sy,px,py=struct.unpack_from('<6d',data,104)
            self.photo_help_transform=({'X':tx,'Y':ty},{'X':sx,'Y':sy},{'X':px,'Y':py})
            self._planner.refresh_from(self._planner._catalog.with_observations(current))
            self.photo_help=help_widget
        if hidden!=self.photo_help_hidden:
            self._render_call(self.photo_help,'Widget','SetRenderOpacity',InOpacity=0. if hidden else self.photo_help_opacity)
            self.photo_help_hidden=hidden

    def set_photo_help_compact(self, compact):
        self.set_photo_help_hidden(False)
        if compact==self.photo_help_compact:return
        translation,scale,pivot=self.photo_help_transform
        self._render_call(self.photo_help,'Widget','SetRenderTransformPivot',Pivot={'X':0.,'Y':0.} if compact else pivot)
        self._render_call(self.photo_help,'Widget','SetRenderTranslation',Translation={'X':0.,'Y':-300.} if compact else translation)
        self._render_call(self.photo_help,'Widget','SetRenderScale',Scale={'X':.55,'Y':.55} if compact else scale)
        self.photo_help_compact=compact

    def show_photo_help(self):
        self.set_text(self.title,'PHOTO MODE | Backspace: Show / hide Scene Editor UI | Home: cursor')
        self.set_text(self.controls_label,'PHOTO MODE CAMERA\nUse the game photo-mode movement controls\nBackspace: Show / hide Scene Editor UI\nPress Backspace again to restore hidden UI + help\nHome: Pin / release timeline cursor\nHold Right Alt: Temporary timeline cursor\nPage Up: Snap camera to current frame\nPeriod (.): Capture camera key at current view\nPage Down: Preview selected animation\nInsert: Open scene menu\nEnd: Stop editor; keep photo mode open')
        for line in self.crosshair:self._render_call(line,'Widget','SetVisibility',InVisibility=self.collapsed)

    def show_help(self, minimized=False):
        self.set_text(self.controls_label,
            'SCENE AUTHORING - FLIGHT\n'
            'Backspace: Show / hide Scene Editor UI\n'
            'Press Backspace again to restore hidden UI + help\n'
            'Home: Pin / release timeline cursor\n'
            'Mouse: Look | WASD: Fly | Shift: Faster\n'
            'Space / E: Up | Ctrl / Q: Down\n'
            'Flight mode: Aim at actor / camera; LMB selects\n'
            'Hold LMB: Carry | Release: Place\n'
            'Numpad 8/2: Forward/back | 6/4: Right/left\n'
            'Numpad 9/3: Up/down | 7/1: Yaw\n'
            'Hold Alt: Precise numpad adjustments\n'
            'Hold Right Alt: Temporary timeline cursor\n'
            'PageDown: Preview selected animation\n'
            'PageUp: View frame camera | Period (.): Camera here\n'
            'End: Stop and restore gameplay\n'
            'Insert: Character / scene browser')

    def show_selection(self, name, axis='', angle=0.):
        self.set_text(self.selection_label,'SELECTED OBJECT\n'+name)

    def close(self):
        if self.photo_help is not None:self.set_photo_help_compact(False)
        if self.widget is not None and self.state != 'closed':
            self._render_call(self.widget,'Widget','RemoveFromParent')
        return super().close()
