"""Stock-menu Picto editor. Owns its widgets; never owns the shared controller."""
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from expedition33.paths import sdk_root, settings_dir
from expedition33 import _reader as sdk_reader, _query
from expedition33.catalog import capture, capture_selected, capture_matching
from expedition33._scope import SessionScope
from expedition33._pause_attachment import PauseAttachment
from expedition33._pause_clicks import PauseClicks
from expedition33.invocation import prepare_call
from expedition33.pause_menu import PauseMenuEntry
from expedition33.management import ModDefinition
from expedition33 import RuntimeQueryError, _ui_batch

log = logging.getLogger(__name__)


def field(values, name):
    keys = [k for k in values.types if k[1] == name]
    if len(keys) != 1 or keys[0] in values.errors:
        detail = values.errors.get(keys[0], '') if len(keys) == 1 else 'ambiguous or missing'
        raise RuntimeError('Unavailable field: ' + name + ': ' + str(detail))
    return values.values[keys[0]]

def same_object(a,b):
    # GC bookkeeping flags can change while UObject identity stays valid.
    return a is b or (a is not None and b is not None and
        (a.pid,a.index,a.serial,a.address)==(b.pid,b.index,b.serial,b.address))


class StockEditor(PauseMenuEntry):
    """Uses existing leased button cleanup and reflected UMG primitives."""
    def __init__(self, scope):
        super().__init__(scope, None)
        self.pid = scope.pid
        self.ui_planner = None
        self.observers = []
        self.labels = []
        self.buttons = []
        self.selection = None
        self._text = {}
        self.message = 'Select a Picto'
        self.pending = None
        self.next_scan = 0
        from expedition33 import values, picto_class_load
        from expedition33.picto_preferences import PictoPreferences
        self.map_reader = sdk_reader
        self.map_values = values
        self.class_loader = picto_class_load
        self.preferences = PictoPreferences(settings_dir() / 'picto-editor.json')
        self.restore_queue = [(identity, mode, key, value)
            for identity, fields in self.preferences.profiles.items()
            for mode, entry in fields.items()
            for key, value in (entry.items() if mode == 'multipliers' else [(None, entry)])]
        self.restore_error = None
        self.definition_id = None
        self.layout_calls = []
        # Share the SDK's operation context, not a persistent runtime cache.
        # Generic reads and candidate map decoding use the same pinned worker.
        self.map_reader._active = sdk_reader._active
        self.map_values._query = _query
        self.stat_rows = {}
        self.stat_key = 1
        self.timings = {}
        self.refresh_worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix='picto-observe')
        self.refresh_future = None
        self.reader_exe = sdk_root() / 'build/readonly-worker/research_probe.exe'
        self.stats = {}
        self.multipliers = {}
        self.view_identity = None
        self.view_item = None
        self.character = None
        self.mode = "stat"
        self.level = None
        self.extra = {}
        self.lumina_ui_pending=False

    def operation(self):
        return self.map_reader.ReadBatch(self.pid,
            _executable=self.reader_exe, share=True)

    def read_stats(self, item):
        values = self.map_values.read_values(self.planner._catalog, item)
        return dict(field(values, 'CurrentStats').items), dict(field(values, 'BaseStatsMultipliers').items)

    def refresh_lumina_ui(self):
        """Repaint the verified compact panel; never rebuild or navigate the menu."""
        with self.operation():
            fresh=capture_matching(self.pid,classes=('WBP_GM_COV_LuminaElement_C','WBP_GM_LuminaPoints_C','BP_PassiveEffectInstance_C','BP_CharacterData_C'))
            c=self.view_catalog.with_observations(fresh)
            prefix=c.path_name(self.panel)+'.'
            updates=[]
            def ref(obj,owner,name):
                nonlocal c
                value,c=self.map_values.read_object_reference(c,obj,c.by_index[c.find_class(owner).index],name)
                return value
            for row in fresh.select('WBP_GM_COV_LuminaElement_C'):
                if row.object_flags&0x30 or not c.path_name(row).startswith(prefix):continue
                passive=ref(row,'WBP_GM_COV_LuminaElement_C','PassiveEffectInstance')
                if passive is None:continue
                pv=self.map_values.read_values(c,passive)
                if not same_object(field(pv,'OwnerData'),self.character):continue
                definition=field(pv,'PassiveDefinition').fields
                label=ref(row,'WBP_GM_COV_LuminaElement_C','LuminaCost')
                if label is not None:updates.append((label,str(definition['LuminaCost_15_BC10A93D48987A14F96279AC521E94CF'])))
            character_values=self.map_values.read_values(c,self.character)
            for counter in fresh.select('WBP_GM_LuminaPoints_C'):
                if counter.object_flags&0x30 or not c.path_name(counter).startswith(prefix):continue
                label=ref(counter,'WBP_GM_LuminaPoints_C','UsedPoints')
                if label is not None:updates.append((label,str(field(character_values,'CurrentlyUsedLuminaPoints'))))
            planner=self.scope.invocation_planner(selected_results=True,catalog=c)
            for label,value in updates:
                with planner.prepare(label,self.fn('TextBlock','SetText'),InText=value).invoke():pass
            return len(updates)

    def reference(self, obj, owner, name):
        found, catalog = self.map_values.read_object_reference(self.planner._catalog,
            obj, self.cls(owner), name)
        self.planner.refresh_from(catalog)
        return found

    def observed_reference(self, values, obj, owner, name):
        key = (self.cls(owner).index, name)
        if key in values.values and key not in values.errors:
            return values.values[key]
        return self.reference(obj, owner, name)

    def install(self):
        started = time.perf_counter()
        with self.operation():
            try:
                # Check the panel before enumerating inventory or building UI.
                panel_catalog = capture_matching(self.pid, classes=('WBP_Panel_Pictos_C',))
                if not any(not o.object_flags & 0x30 and field(self.map_values.read_values(panel_catalog, o), 'bIsActive')
                           for o in panel_catalog.select('WBP_Panel_Pictos_C')):
                    return False
                c = capture_matching(self.pid, names=(
                    'WBP_BaseButton_C', 'CommonButtonBase', 'CommonActivatableWidget', 'CommonTextBlock', 'TextBlock',
                    'TextLayoutWidget', 'Widget', 'UserWidget', 'GridPanel', 'GridSlot',
                    'PanelSlot', 'ContentWidget', 'CanvasPanel', 'CanvasPanelSlot', 'CTS_B1_SmallLine_Outline_C',
                    'WidgetBlueprintLibrary', 'GameplayStatics', 'Default__WidgetBlueprintLibrary', 'Default__GameplayStatics', 'Create',
                    'SpawnObject', 'SetContent', 'GetContent', 'AddChildToGrid', 'AddChildToCanvas',
                    'SetPosition', 'SetSize', 'SetPadding', 'SetHorizontalAlignment', 'SetVerticalAlignment',
                    'SetText', 'SetStyle', 'SetMinDimensions', 'SetIsSelectable', 'SetIsToggleable',
                    'RemoveFromParent', 'HandleButtonClicked', 'SetRenderTransformPivot', 'SetRenderScale', 'SetLayer',
                    'SetIsEnabled', 'SetBaseStatsMultiplier', 'RefreshCurrentGearStats', 'ChangeLevel', 'SetPassiveEffectSharedProgression',
                    'RefreshUsedLuminaPointsInternal', 'UpdateEquipmentStats', 'RefreshSlotData', 'DT_PassiveEffects', 'S_jRPG_Item_DynamicData',
                    'S_jRPG_Item_StaticData', 'FPassiveEffect', 'FPassiveEffectProgression', 'FCharacterAssignedEquipment', 'FEquipmentSlot',
                    'PointerToUberGraphFrame', 'S_GearScalingLevel', 'S_LootContext', 'Margin', 'Vector2D',
                    'LinearColor', 'Anchors', 'WidgetTransform', 'EHorizontalAlignment', 'EVerticalAlignment',
                    'E_jRPG_StatType', 'AnimationEventBinding', 'AudioComponent', 'ButtonStyle', 'CommonActionWidget',
                    'CommonButtonBaseClicked__DelegateSignature', 'CommonButtonStyle', 'CommonLazyImage', 'CommonSelectedStateChangedBase__DelegateSignature', 'CommonUIHoldData',
                    'DataTableRowHandle', 'EButtonClickMethod', 'EButtonPressMethod', 'EButtonTouchMethod', 'ECommonInputMode',
                    'EFlowDirectionPreference', 'EMouseCursor', 'EOrientation', 'ESlateVisibility', 'EWidgetClipping',
                    'EWidgetPixelSnapping', 'EWidgetTickFrequency', 'InputAction', 'InputComponent', 'MaterialInstance',
                    'MaterialInstanceDynamic', 'NamedSlot', 'NamedSlotBinding', 'OnButtonBaseActionProgress__DelegateSignature', 'OnButtonBaseFocusedHold__DelegateSignature',
                    'OnButtonBaseFocused__DelegateSignature', 'OnButtonBaseUnfocused__DelegateSignature', 'OnConstrainedNavigationTriggered__DelegateSignature', 'OnVisibilityChangedEvent__DelegateSignature', 'PropertyBinding',
                    'QueuedWidgetAnimationTransition', 'RetainerBox', 'SlateAccessibleWidgetData', 'SlateColor', 'SlateSound',
                    'SoundEventDataTableRowHandle', 'TimerHandle', 'UMGSequencePlayer', 'UMGSequenceTickManager', 'UserWidgetExtension',
                    'WidgetAnimation', 'WidgetChild', 'WidgetEventField', 'WidgetNavigation',
                ), classes=('WBP_Panel_Pictos_C', 'PlayerController', 'LocalPlayer',
                    'BP_ItemInstance_Gear_Pictos_C', 'BP_PassiveEffectInstance_C',
                    'BP_CharacterData_C', 'BP_jRPG_GI_Custom_C'))
            except RuntimeQueryError as error:
                # A read-only full snapshot can race transient widget cleanup.
                # No widgets or mutations exist yet; retry on the next poll.
                if self.error != str(error):
                    log.warning('Picto discovery deferred: %s', error)
                self.error = str(error)
                return False
            self.timings['catalog_ms'] = round((time.perf_counter() - started) * 1000, 1)
            stage = time.perf_counter()
            self.inventory = {}
            self.inventory_ready = False
            self.inventory_candidates = tuple(o for o in c.select('BP_ItemInstance_Gear_Pictos_C')
                if o.class_name == 'BP_ItemInstance_Gear_Pictos_C' and not o.object_flags & 0x30)
            self.timings['inventory_ms'] = round((time.perf_counter() - stage) * 1000, 1)
            stage = time.perf_counter()
            panels = [o for o in c.select('WBP_Panel_Pictos_C')
                if not o.object_flags & 0x30 and field(self.map_values.read_values(c, o), 'bIsActive')]
            if not panels:
                return False
            self.panel = self.one(panels)
            self.player = self.one(o for o in c.select('PlayerController')
                if not o.object_flags & 0x30 and any(k[1] == 'Player' and
                    getattr(v, 'class_name', '') == 'LocalPlayer'
                    for k, v in self.map_values.read_values(c, o).values.items()))
            self.game_instance = self.one(o for o in c.select('BP_jRPG_GI_Custom_C') if not o.object_flags & 0x30)
            self.passive_table = self.one(o for o in c.objects if o.class_name=='DataTable' and c.path_name(o)=='/Game/Gameplay/Lumina/DT_PassiveEffects.DT_PassiveEffects')
            self.passives = {}
            # Resolve passive instances lazily after the menu is visible.
            self.view_catalog = c
            keep = {self.player.index, self.panel.index, *(v.index for v in self.inventory_candidates)}
            c = c.subset(o for o in c.objects if o.index in keep or o.index in c.classes or
                o.class_name in ('Function','DelegateFunction','SparseDelegateFunction','ScriptStruct','UserDefinedStruct','Enum','UserDefinedEnum') or
                o.name in ('Default__WidgetBlueprintLibrary','Default__GameplayStatics'))
            self.timings['resolve_ms'] = round((time.perf_counter() - stage) * 1000, 1)
            stage = time.perf_counter()
            self.scope = SessionScope(self.parent_scope)
            self.state = 'building'
            self.planner = self.scope.invocation_planner(selected_results=True, catalog=c)
            library = self.one(o for o in c.objects if o.name == 'Default__WidgetBlueprintLibrary')
            self.gameplay = self.one(o for o in c.objects if o.name == 'Default__GameplayStatics')
            tree = self.reference(self.panel, 'UserWidget', 'WidgetTree')
            self.host = self.reference(tree, 'WidgetTree', 'RootWidget')
            if self.host.class_name == 'SafeZone':
                self.host = self.create(self.host, 'ContentWidget', 'GetContent')
            if self.host.class_name != 'GridPanel':
                raise RuntimeError('Stock Picto root is not the verified GridPanel: ' + self.host.class_name)
            self.root = self.create(library, 'WidgetBlueprintLibrary', 'Create',
                WorldContextObject=self.player, WidgetType=self.cls('WBP_BaseButton_C'), OwningPlayer=self.player)
            # This owned stock button is only a cleanup container. Its child
            # buttons keep their animations; the container must never scale them.
            for name in ('Anim_Hover', 'Anim_Pressed', 'Anim_Selected'):
                animation = self.reference(self.root, 'WBP_BaseButton_C', name)
                self.scope.assign_object(self.root, self.cls('WBP_BaseButton_C'), name,
                    None, expected=animation, allow_mutation=True, catalog=self.planner._catalog)
                if self.reference(self.root, 'WBP_BaseButton_C', name) is not None:
                    raise RuntimeError('Container animation removal did not read back')
            self.call(self.root, 'CommonButtonBase', 'SetIsSelectable', bInIsSelectable=False)
            self.call(self.root, 'CommonButtonBase', 'SetIsToggleable', bInIsToggleable=False)
            self.attachment = PauseAttachment(self.scope)
            lease = self.one(l for l in self.scope._leases if l.active and l.object == self.root)
            self.attachment.arm(lease, prepare_call(self.planner._catalog, self.root,
                self.fn('Widget', 'RemoveFromParent'), {}))
            self.tree = self.reference(self.root, 'UserWidget', 'WidgetTree')
            self.canvas = self.spawn('CanvasPanel')
            content = self.reference(self.root, 'WBP_BaseButton_C', 'ButtonContent')
            self.call(content, 'ContentWidget', 'SetContent', Content=self.canvas)
            self.style = self.cls('CTS_B1_SmallLine_Outline_C')
            self.header = self.make_label('PICTO EDITOR', 12, 6, 580, 36)
            self.value_label = self.make_label('Select a field', 12, 186, 580, 35)
            self.status_label = self.make_label('Draft changes; Apply to commit', 12, 222, 580, 35)
            # Every available stat is directly selectable, including zero values.
            for key, name in ((1, 'Health'), (6, 'Defense'), (8, 'Speed'), (9, 'Crit Rate')):
                button, text = self.make_button(library, name, 12, 43 + len(self.stat_rows) * 35, 270, 32)
                self.stat_rows[key] = (button, text, name)
            self.adjust_labels = []
            for i, title in enumerate(('- 0.1', '+ 0.1', 'Apply')):
                _, text = self.make_button(library, title, 300 + i * 98, 145, 92, 36)
                self.adjust_labels.append(text)
            self.level_button, self.level_label = self.make_button(library, 'Level', 300, 43, 285, 32)
            self.mastery_button, self.mastery_label = self.make_button(library, 'Mastery', 300, 78, 285, 32)
            self.cost_button, self.cost_label = self.make_button(library, 'Lumina cost', 300, 113, 285, 32)
            self.flush_layout()
            self.call(self.root, 'CommonButtonBase', 'SetMinDimensions', InMinWidth=610, InMinHeight=264)
            self.call(self.root, 'Widget', 'SetRenderTransformPivot', Pivot={'X':0., 'Y':0.})
            self.call(self.root, 'Widget', 'SetRenderScale', Scale={'X':.8, 'Y':.8})
            slot = self.create(self.host, 'GridPanel', 'AddChildToGrid', Content=self.root, InRow=0, InColumn=0)
            self.call(slot, 'GridSlot', 'SetPadding', InPadding={'Left':770., 'Top':80., 'Right':0., 'Bottom':0.})
            self.call(slot, 'GridSlot', 'SetHorizontalAlignment', InHorizontalAlignment=1)
            self.call(slot, 'GridSlot', 'SetVerticalAlignment', InVerticalAlignment=1)
            self.call(slot, 'GridSlot', 'SetLayer', InLayer=100)
            self.writes_available = getattr(self.scope._session._transport, 'picto_edit_protocol', 0) == 1
            self.call(self.buttons[6], 'Widget', 'SetIsEnabled', bInIsEnabled=self.writes_available)
            self.progression_available = getattr(self.scope._session._transport, 'picto_progression_protocol', 0)==1
            for button in (self.level_button, self.mastery_button):
                self.call(button, 'Widget', 'SetIsEnabled', bInIsEnabled=self.progression_available)
            self.cost_available=getattr(self.scope._session._transport,'picto_cost_protocol',0)==1
            self.call(self.cost_button,'Widget','SetIsEnabled',bInIsEnabled=self.cost_available)
            self.ui_planner = self.scope.invocation_planner(selected_results=True, catalog=self.planner._catalog)
            self.ui_planner.prepare(self.header, self.fn('TextBlock', 'SetText'), InText='PICTO EDITOR')
            self.timings['widgets_ms'] = round((time.perf_counter() - stage) * 1000, 1)
            self.timings['attach_ms'] = round((time.perf_counter() - started) * 1000, 1)
            self.error = None
            self.state = 'attached'
            self._renew_at = time.monotonic() + 120
            log.info('Picto editor attached to current stock panel %s', self.panel.index)
            return True

    def defer_layout(self, obj, owner, name, **args):
        if not _ui_batch.layout_available(self.scope._session):
            return self.call(obj, owner, name, **args)
        # Widget creation refreshes the catalog and revokes prepared calls.
        # Keep arguments until the batch is ready, then prepare together.
        self.layout_calls.append((obj, owner, name, args))
        if len(self.layout_calls) >= 16:
            self.flush_layout()

    def flush_layout(self):
        if self.layout_calls:
            calls, self.layout_calls = self.layout_calls, []
            _ui_batch.invoke_setters(self.scope, [self.planner.prepare(obj, self.fn(owner, name), **args)
                for obj, owner, name, args in calls])

    def make_button(self, library, title, x, y, width, height):
        button = self.create(library, 'WidgetBlueprintLibrary', 'Create',
            WorldContextObject=self.player, WidgetType=self.cls('WBP_BaseButton_C'), OwningPlayer=self.player)
        self.call(button, 'CommonButtonBase', 'SetMinDimensions', InMinWidth=width, InMinHeight=height)
        content = self.reference(button, 'WBP_BaseButton_C', 'ButtonContent')
        text = self.spawn('CommonTextBlock')
        self.defer_layout(text, 'CommonTextBlock', 'SetStyle', InStyle=self.style)
        self.defer_layout(text, 'TextBlock', 'SetText', InText=title)
        self.call(content, 'ContentWidget', 'SetContent', Content=text)
        self.place(self.canvas, button, x, y, width, height)
        self.buttons.append(button)
        self.observers.append(PauseClicks(self.scope._session,
            self.fn('CommonButtonBase', 'HandleButtonClicked'), button, self.planner._catalog))
        return button, text

    def spawn(self, name):
        return self.create(self.gameplay, 'GameplayStatics', 'SpawnObject',
            ObjectClass=self.cls(name), Outer=self.tree)

    def place(self, parent, child, x, y, w, h):
        slot = self.create(parent, 'CanvasPanel', 'AddChildToCanvas', Content=child)
        self.defer_layout(slot, 'CanvasPanelSlot', 'SetPosition', InPosition={'X': float(x), 'Y': float(y)})
        self.defer_layout(slot, 'CanvasPanelSlot', 'SetSize', InSize={'X': float(w), 'Y': float(h)})

    def make_label(self, text, x, y, w, h):
        label = self.spawn('CommonTextBlock')
        self.defer_layout(label, 'CommonTextBlock', 'SetStyle', InStyle=self.style)
        self.defer_layout(label, 'TextBlock', 'SetText', InText=text)
        self.place(self.canvas, label, x, y, w, h)
        return label

    def text(self, label, value):
        if self._text.get(label.index) != value:
            planner = self.ui_planner or self.planner
            with planner.prepare(label, self.fn('TextBlock', 'SetText'), InText=value).invoke() as result:
                pass
            self._text[label.index] = value

    def observe(self, catalog, view_catalog):
        # Read-only worker thread: owns its short-lived native reader and local
        # catalogues. It never invokes UFunctions or changes session resources.
        started = time.perf_counter()
        with self.operation():
            values = self.map_values.read_values(catalog, self.panel)
            if not field(values, 'bIsActive'):
                return catalog, view_catalog, None, None, None, {}, time.perf_counter() - started
            def ref(obj, owner, name, observed=None):
                nonlocal catalog
                key = (catalog.find_class(owner).index, name)
                if observed is not None and key in observed.values and key not in observed.errors:
                    return observed.values[key]
                value, catalog = self.map_values.read_object_reference(catalog, obj,
                    catalog.by_index[catalog.find_class(owner).index], name)
                return value
            if not self.inventory_ready:
                inventory = {}
                for candidate in self.inventory_candidates:
                    identity = field(self.map_values.read_values(catalog, candidate), 'ItemDefinitionID')
                    if identity in inventory:
                        raise RuntimeError('Ambiguous Picto inventory identity: ' + identity)
                    inventory[identity] = candidate
                self.inventory = inventory
                self.inventory_ready = True
            character = ref(self.panel, 'WBP_Panel_Pictos_C', 'CurrentCharacterData', values)
            view = ref(self.panel, 'WBP_Panel_Pictos_C', 'FocusedItem', values) or ref(
                self.panel, 'WBP_Panel_Pictos_C', 'SelectedPictoViewItem', values)
            if view is None:
                slot = ref(self.panel, 'WBP_Panel_Pictos_C', 'FocusedSlot', values)
                if slot is not None:
                    view = ref(slot, 'WBP_PictoSlot_C', 'Picto View Item')
            if view is None:
                return catalog, view_catalog, character, None, None, {}, time.perf_counter() - started
            if view.class_name != 'BP_PictoViewItem_C':
                raise RuntimeError('Focused item is not a Picto view item')
            if view_catalog.by_index.get(view.index) != view:
                fresh = capture_selected(self.pid, ((view.index, view.serial, view.address),))
                view_catalog = view_catalog.with_observations(fresh)
            view_values, view_catalog = self.map_values.read_values_with_references(view_catalog, view)
            dynamic = field(view_values, 'ItemDynamicData')
            static = dynamic.fields['ItemStaticData_9_59CF465348F5D7696BDFE68CB4071486']
            identity = static.fields['Item_HardcodedName_90_C7F763B74AAB28EF890A66854D7D95AA']
            item = self.inventory.get(identity)
            if item is None or item.class_name != 'BP_ItemInstance_Gear_Pictos_C':
                raise RuntimeError('No exact owned Picto for selection')
            values = self.map_values.read_values(catalog, item)
            extra = {}
            passive = self.passives.get((character.index, identity)) if character else None
            if passive is None and character is not None:
                fresh=capture_matching(self.pid,classes=('BP_PassiveEffectInstance_C','BP_CharacterData_C'))
                view_catalog=view_catalog.with_observations(fresh)
                for obj in fresh.select('BP_PassiveEffectInstance_C'):
                    if obj.object_flags&0x30:continue
                    observed=self.map_values.read_values(view_catalog,obj)
                    owner=field(observed,'OwnerData')
                    if owner is not None:self.passives[(owner.index,field(observed,'PassiveEffectID'))]=obj
                passive=self.passives.get((character.index,identity))
            if passive is not None:
                pv = self.map_values.read_values(view_catalog, passive)
                if not same_object(field(pv,'OwnerData'),character) or field(pv,'PassiveEffectID') != identity:
                    raise RuntimeError('Passive definition selection changed')
                definition = field(pv,'PassiveDefinition').fields
                shared = field(self.map_values.read_values(view_catalog,self.game_instance), 'SharedPassiveEffectProgression').items
                progression = shared.get(identity)
                extra = {'source':passive, 'cost':definition['LuminaCost_15_BC10A93D48987A14F96279AC521E94CF'],
                    'threshold':definition['LuminaUnlockStepsCount_19_B80447FF455A4D693EAD2991AD473004'],
                    'steps':progression.fields['LearntSteps_6_A14D681549E830249C77BD95F2B4CF3F'] if progression else 0,
                    'mastered':progression.fields['IsLearnt_9_2561000E49D90653437DE9A45BE2A86D'] if progression else False}
            return catalog, view_catalog, character, item, values, extra, time.perf_counter() - started

    def accept_observation(self, result):
        catalog, self.view_catalog, character, item, values, self.extra, elapsed = result
        # Merge into the owner thread's current catalogue, preserving owned widgets.
        self.planner.refresh_from(self.planner._catalog.with_observations(catalog))
        if not same_object(item,self.selection) or not same_object(character,self.character):
            self.selection, self.pending = item, None
        self.character = character
        self.timings['refresh_ms'] = round(elapsed * 1000, 1)
        if item is None:
            self.text(self.value_label, 'Select a Picto')
            for button, text, name in self.stat_rows.values():
                self.text(text, name + ': --')
            return
        self.text(self.header, 'PICTO EDITOR | ' + field(values, 'ItemDefinitionID') +
            ' | Lv ' + str(field(values, 'CurrentLevel')))
        self.definition_id = field(values, 'ItemDefinitionID')
        self.level = field(values, 'CurrentLevel')
        self.stats = dict(field(values, 'CurrentStats').items)
        self.multipliers = dict(field(values, 'BaseStatsMultipliers').items)
        self.paint_value()

    def refresh_current(self):
        # Apply requires a fresh observation; discard older background work.
        if self.refresh_future is not None:
            self.refresh_future.result()
            self.refresh_future = None
        self.accept_observation(self.observe(self.planner._catalog, self.view_catalog))

    def paint_value(self):
        keys = sorted(self.multipliers)
        if not keys:
            raise RuntimeError('No verified stat multiplier keys')
        if self.stat_key not in keys:
            self.stat_key = keys[0]
        for key, (button, text, name) in self.stat_rows.items():
            available = key in self.multipliers
            marker = '> ' if self.mode == 'stat' and key == self.stat_key else ''
            value = (f'{self.stats.get(key, 0):g}' + ('%' if key == 9 else '')) if available else 'unavailable'
            self.text(text, f'{marker}{name}: {value}')
        self.text(self.level_label, ('> ' if self.mode=='level' else '')+f'Level: {self.level}')
        mastery = ('Mastered' if self.extra.get('mastered') else 'Unmastered') if self.extra else 'unavailable'
        self.text(self.mastery_label, ('> ' if self.mode=='mastery' else '')+'Mastery: '+mastery)
        self.text(self.cost_label, ('> ' if self.mode=='cost' else '')+(f"Lumina cost: {self.extra['cost']}" if self.extra else 'Lumina cost: unavailable'))
        if self.mode=='stat':
            value = self.multipliers[self.stat_key] if self.pending is None else self.pending
            label=f'Multiplier {value:g}'; minus,plus='- 0.1','+ 0.1'
        elif self.mode=='level':
            value = self.level if self.pending is None else self.pending
            label=f'Level {value}';minus,plus='- 1','+ 1'
        elif self.mode=='cost':
            value=self.extra.get('cost',0) if self.pending is None else self.pending
            label=f'Lumina cost {value} (all characters)';minus,plus='- 1','+ 1'
        else:
            value=self.extra.get('steps',0) if self.pending is None else self.pending
            label=f"Shared mastery: {value}/{self.extra.get('threshold','?')}";minus,plus='Reset','Master'
        self.text(self.value_label, label+(' *' if self.pending is not None else ''))
        self.text(self.adjust_labels[0],minus);self.text(self.adjust_labels[1],plus)

    def activate(self,index):
        started=time.perf_counter()
        if self.selection is None:return
        if index!=6:
            if index<4:
                self.mode='stat';self.stat_key=tuple(self.stat_rows)[index];self.pending=None
            elif index in (7,8):
                if not self.progression_available or (index==8 and not self.extra):return
                self.mode='level' if index==7 else 'mastery';self.pending=None
            elif index==9:
                if not self.cost_available or not self.extra:return
                self.mode='cost';self.pending=None
            elif index in (4,5):
                if self.mode=='stat':
                    value=self.multipliers[self.stat_key] if self.pending is None else self.pending
                    self.pending=round(max(0.,min(10.,value+(-.1 if index==4 else .1))),3)
                elif self.mode=='level':
                    value=self.level if self.pending is None else self.pending
                    self.pending=max(1,min(33,value+(-1 if index==4 else 1)))
                elif self.mode=='cost' and self.extra:
                    value=self.extra['cost'] if self.pending is None else self.pending
                    self.pending=max(0,min(100,value+(-1 if index==4 else 1)))
                elif self.extra:
                    self.pending=0 if index==4 else self.extra['threshold']
            self.paint_value()
            self.timings['draft_ms']=round((time.perf_counter()-started)*1000,1)
            return
        if self.pending is None:return
        previous,character=self.selection,self.character
        mode,value,key=self.mode,self.pending,self.stat_key
        baseline=self.multipliers.get(key) if mode=='stat' else self.level if mode=='level' else self.extra.get('cost' if mode=='cost' else 'steps')
        self.refresh_current()
        if not same_object(self.selection,previous) or not same_object(self.character,character):
            self.pending=None;self.text(self.status_label,'Selection changed; draft discarded');return
        current=self.multipliers.get(key) if mode=='stat' else self.level if mode=='level' else self.extra.get('cost' if mode=='cost' else 'steps')
        if current!=baseline:
            self.pending=None;self.text(self.status_label,'Value changed; draft discarded');self.paint_value();return
        with self.operation():
            if mode=='stat':
                self.call(previous,'BP_ItemInstance_Gear_C','SetBaseStatsMultiplier',Stat=key,Value=value)
                self.call(previous,'BP_ItemInstance_Gear_C','RefreshCurrentGearStats')
                self.stats,self.multipliers=self.read_stats(previous)
                if self.multipliers[key]!=value:raise RuntimeError('Stat readback mismatch')
            else:
                from expedition33.picto_progression import change
                if mode=='level':
                    change(self.scope,1,previous,self.fn('BP_ItemInstance_Gear_C','ChangeLevel'),None,self.panel,None,baseline,value)
                    self.level=value;self.stats,self.multipliers=self.read_stats(previous)
                elif mode=='cost':
                    change(self.scope,3,self.passive_table,self.fn('BP_CharacterData_C','RefreshUsedLuminaPointsInternal'),
                        self.extra['source'],self.panel,character,baseline,value)
                else:
                    change(self.scope,2,character,self.fn('BP_CharacterData_C','SetPassiveEffectSharedProgression'),
                        self.extra['source'],self.panel,self.game_instance,baseline,value)
            self.preferences.remember(self.definition_id, mode, bool(value) if mode == 'mastery' else value, key)
            saved_mode = {'stat': 'multipliers', 'mastery': 'mastered'}.get(mode, mode)
            self.restore_queue = [entry for entry in self.restore_queue if not (entry[0] == self.definition_id and entry[1] == saved_mode and (mode != 'stat' or entry[2] == str(key)))]
            self.call(character,'BP_CharacterData_C','UpdateEquipmentStats')
            for slot in range(3):self.call(self.panel,'WBP_Panel_Pictos_C','RefreshSlotData',InSlotIndex=slot)
        self.pending=None
        if mode=='cost':
            try:self.refresh_lumina_ui()
            except RuntimeQueryError:
                # The cost was already acknowledged. Retry only its display refresh.
                self.lumina_ui_pending=True
        self.refresh_current()
        self.text(self.status_label,'Applied and saved' if mode!='mastery' else 'Mastery updated and saved')
        self.timings['action_ms']=round((time.perf_counter()-started)*1000,1)

    def poll(self):
        if self.state in ('failed', 'closed'):
            return
        now = time.monotonic()
        try:
            if self.state == 'new':
                if now >= self.next_scan:
                    self.next_scan = now + 2
                    self.install()
                return
            for i, observer in enumerate(self.observers):
                if observer.state != 'active':
                    raise RuntimeError('Editor click observer expired')
                for event in observer.read():
                    self.activate(i)
            if now >= self._renew_at:
                self.observers[0].renew()
                self._renew_at = now + 120
            if self.lumina_ui_pending and self.selection is not None:
                try:self.refresh_lumina_ui()
                except RuntimeQueryError:pass
                else:self.lumina_ui_pending=False
            if self.refresh_future is not None and self.refresh_future.done():
                future=self.refresh_future
                self.refresh_future = None
                try:
                    result=future.result()
                except RuntimeQueryError:
                    # Only a read failed: discard recycled identities and rediscover.
                    # Mutation exceptions take the separate fail-closed path below.
                    self.passives={}
                    self.next_scan=now+.1
                else:
                    self.accept_observation(result)
            if self.restore_queue and not self.restore_error and self.refresh_future is None and self.character is not None:
                self.restore_one()
            if self.refresh_future is None and now >= self.next_scan:
                self.next_scan = now + .1
                self.refresh_future = self.refresh_worker.submit(self.observe,
                    self.planner._catalog, self.view_catalog)
        except BaseException as error:
            self.error = str(error)
            self.state = 'failed'
            log.exception('Picto editor suspended; retained for explicit cleanup')

    def restore_one(self):
        """Restore one saved field with fresh reads; never retry uncertain writes.

        Native operations require an active stock panel. Missing inventory is
        left unmodified. The file contains only explicit user overrides.
        """
        identity, mode, key, value = self.restore_queue[0]
        required = self.writes_available if mode == 'multipliers' else self.cost_available if mode == 'cost' else self.progression_available
        if not required:
            self.restore_error = 'This controller lacks Picto editing capabilities; saved settings retained'
            return
        try:
            self.refresh_current()
            if self.character is None or self.selection is None:
                return
            with self.operation():
                panel_values = self.map_values.read_values(self.planner._catalog, self.panel)
                if not field(panel_values, 'bIsActive'):
                    return
                item = self.inventory.get(identity)
                if item is None:
                    # Another save may not own this Picto. Keep its file entry.
                    self.restore_queue.pop(0)
                    return
                observed = self.map_values.read_values(self.planner._catalog, item)
                if field(observed, 'ItemDefinitionID') != identity:
                    raise RuntimeError('Saved Picto identity changed')
                changed = False
                from expedition33.picto_progression import change
                if mode == 'multipliers':
                    stat = int(key)
                    current = dict(field(observed, 'BaseStatsMultipliers').items)[stat]
                    if current != value:
                        self.call(item, 'BP_ItemInstance_Gear_C', 'SetBaseStatsMultiplier', Stat=stat, Value=value)
                        self.call(item, 'BP_ItemInstance_Gear_C', 'RefreshCurrentGearStats')
                        if self.read_stats(item)[1][stat] != value:
                            raise RuntimeError('Restored stat readback mismatch')
                        changed = True
                elif mode == 'level':
                    current = field(observed, 'CurrentLevel')
                    if current != value:
                        change(self.scope, 1, item, self.fn('BP_ItemInstance_Gear_C', 'ChangeLevel'), None, self.panel, None, current, value)
                        changed = True
                else:
                    source = self.passives.get((self.character.index, identity))
                    if source is None:
                        raise RuntimeError('Saved Picto passive not resolved: ' + identity)
                    passive = self.map_values.read_values(self.view_catalog, source)
                    if not same_object(field(passive, 'OwnerData'), self.character) or field(passive, 'PassiveEffectID') != identity:
                        raise RuntimeError('Saved Picto passive identity changed')
                    definition = field(passive, 'PassiveDefinition').fields
                    if mode == 'cost':
                        current = definition['LuminaCost_15_BC10A93D48987A14F96279AC521E94CF']
                        if current != value:
                            change(self.scope, 3, self.passive_table, self.fn('BP_CharacterData_C', 'RefreshUsedLuminaPointsInternal'), source, self.panel, self.character, current, value)
                            self.lumina_ui_pending = True
                            changed = True
                    else:
                        shared = field(self.map_values.read_values(self.view_catalog, self.game_instance), 'SharedPassiveEffectProgression').items
                        progress = shared.get(identity)
                        mastered = progress.fields['IsLearnt_9_2561000E49D90653437DE9A45BE2A86D'] if progress else False
                        if mastered != value:
                            steps = progress.fields['LearntSteps_6_A14D681549E830249C77BD95F2B4CF3F'] if progress else 0
                            target = definition['LuminaUnlockStepsCount_19_B80447FF455A4D693EAD2991AD473004'] if value else 0
                            change(self.scope, 2, self.character, self.fn('BP_CharacterData_C', 'SetPassiveEffectSharedProgression'), source, self.panel, self.game_instance, steps, target)
                            changed = True
                # Remove only after confirmed completion. A failure below must
                # not resend a mutation whose acknowledgement already succeeded.
                self.restore_queue.pop(0)
                if changed:
                    self.call(self.character, 'BP_CharacterData_C', 'UpdateEquipmentStats')
                    for slot in range(3):
                        self.call(self.panel, 'WBP_Panel_Pictos_C', 'RefreshSlotData', InSlotIndex=slot)
                self.text(self.status_label, 'Restored saved Picto settings' if not self.restore_queue else 'Restoring saved Picto settings...')
        except Exception as error:
            self.restore_error = str(error)
            log.exception('Picto restoration stopped; saved configuration retained')
            self.text(self.status_label, 'Restore stopped; see diagnostics')

    def close(self):
        self.refresh_worker.shutdown(wait=True, cancel_futures=True)
        for observer in self.observers:
            observer.close()
        self.observers.clear()
        if self.attachment is not None and not self.attachment.close():
            raise RuntimeError('Editor detach deferred; retain owner')
        if self.scope is not None:
            self.scope.close()
        self.state = 'closed'


class Mod:
    def management(self):
        return ModDefinition('sdk.picto-editor', 'Picto Editor', version='0.5.0',
            description='Live controls attached to the stock Pictos menu.')

    def enable(self, session):
        self.session = session
        self.editor = StockEditor(session)
        session.console.expose('picto_editor', self)
        session.actions.register('picto.status', self.status, mutates=False)
        session.actions.register('picto.load_combo_definition', self.load_combo_definition, mutates=True)
        session.actions.register('picto.verify_progression', self.verify_progression, mutates=True)
        session.actions.register('picto.refresh_lumina_ui', self.refresh_lumina_ui, mutates=True)
        session.actions.register('picto.verify_saved_restore', self.verify_saved_restore, mutates=True)

    def verify_saved_restore(self, _=None):
        """Exercise restoration using a one-point transient cost change.

        Only an already-saved, currently selected cost is eligible. This never
        edits the preferences file or saves the game. A failed/unknown mutation
        stops immediately; no guessed rollback or blind retry occurs.
        """
        from expedition33.picto_progression import change
        e = self.editor
        e.refresh_current()
        if e.restore_queue or e.restore_error or e.selection is None or not e.extra:
            raise RuntimeError('Editor must be ready with completed restoration')
        saved = type(e.preferences)(e.preferences.store.path)
        identity = e.definition_id
        baseline = saved.profiles.get(identity, {}).get('cost')
        if baseline is None or baseline != e.extra['cost']:
            raise RuntimeError('Select a Picto whose saved cost matches its current cost')
        trial = baseline - 1 if baseline else 1
        observed = change(e.scope, 3, e.passive_table,
            e.fn('BP_CharacterData_C', 'RefreshUsedLuminaPointsInternal'),
            e.extra['source'], e.panel, e.character, baseline, trial)
        # Reconstruct the queue from a newly opened settings file, exactly as
        # after mod/controller startup. Preserve the original settings owner.
        e.restore_queue = [(identity, 'cost', None, saved.profiles[identity]['cost'])]
        e.restore_one()
        if e.restore_error or e.restore_queue:
            raise RuntimeError('Saved restoration failed: ' + str(e.restore_error))
        e.refresh_current()
        if e.definition_id != identity or e.extra['cost'] != baseline:
            raise RuntimeError('Restored cost readback or selection changed')
        return {'picto': identity, 'saved': baseline, 'temporary': observed,
                'restored': e.extra['cost'], 'configuration_revision': saved.store.revision}

    def refresh_lumina_ui(self, _=None):
        return {'labels_refreshed':self.editor.refresh_lumina_ui()}

    def verify_cost(self, _=None):
        from expedition33.picto_progression import change
        e=self.editor;e.refresh_current()
        if e.selection is None or not e.extra:raise RuntimeError('Select a Picto with a verified passive')
        baseline=e.extra['cost'];trial=baseline-1 if baseline else 1
        source,character=e.extra['source'],e.character
        def points():
            with e.operation():
                c=capture()
                return {str(o.index):field(e.map_values.read_values(c,o),'CurrentlyUsedLuminaPoints')
                    for o in c.select('BP_CharacterData_C') if not o.object_flags&0x30}
        before=points()
        observed=change(e.scope,3,e.passive_table,e.fn('BP_CharacterData_C','RefreshUsedLuminaPointsInternal'),source,e.panel,character,baseline,trial)
        after=points()
        # Restore only after an unambiguous acknowledged write, never on unknown outcome.
        restored=change(e.scope,3,e.passive_table,e.fn('BP_CharacterData_C','RefreshUsedLuminaPointsInternal'),source,e.panel,character,trial,baseline)
        final=points();e.refresh_current()
        return {'baseline':baseline,'trial':observed,'restored':restored,'menu_cost':e.extra['cost'],
            'points_before':before,'points_trial':after,'points_restored':final}

    def verify_progression(self, _=None):
        from expedition33.picto_progression import change
        e=self.editor;e.refresh_current()
        if e.selection is None or not e.extra:raise RuntimeError('Select a Picto with a verified passive')
        level,steps=e.level,e.extra['steps']
        result_level=change(e.scope,1,e.selection,e.fn('BP_ItemInstance_Gear_C','ChangeLevel'),None,e.panel,None,level,level)
        result_steps=change(e.scope,2,e.character,e.fn('BP_CharacterData_C','SetPassiveEffectSharedProgression'),e.extra['source'],e.panel,e.game_instance,steps,steps) if steps<=100 else 'Skipped no-op: accumulated steps exceed setter target bound'
        e.refresh_current()
        return {'noop':True,'level_before':level,'level_after':result_level,'steps_before':steps,'steps_after':result_steps,'mastered':e.extra.get('mastered')}

    def load_combo_definition(self, _=None):
        load_class = self.editor.class_loader.load_class
        if getattr(self, 'combo_class_result', None) is None:
            self.combo_class_result=load_class(self.editor.scope,
                '/Game/Gameplay/Lumina/Passives/OnActivateBuff/BP_LU_ComboAttackC.BP_LU_ComboAttackC_C')
        obj=self.combo_class_result.return_value
        return {'index':obj.index,'serial':obj.serial,'address':obj.address,'name':obj.name}

    def status(self, _=None):
        return {'state': self.editor.state, 'error': self.editor.error, 'capabilities': {name: getattr(self.editor, name, False) for name in ('writes_available', 'progression_available', 'cost_available')}, 'saved_pictos': len(self.editor.preferences.profiles), 'restore_pending': len(self.editor.restore_queue), 'restore_error': self.editor.restore_error, 'timings': dict(self.editor.timings), 'mode':self.editor.mode, 'level':self.editor.level, 'mastery':{k:v for k,v in self.editor.extra.items() if k!='source'}}

    def poll(self):
        self.editor.poll()

    def disable(self):
        self.editor.close()

