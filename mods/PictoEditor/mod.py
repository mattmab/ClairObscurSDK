"""Stock-menu Picto editor. Owns its widgets; never owns the shared controller."""
import logging
import time
import threading
from contextlib import contextmanager
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
from expedition33.picto_drafts import PictoDraft, preview_stats

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


def runtime_widget(catalog, obj):
    """Exclude CDOs and widget-tree templates owned by a Blueprint class."""
    seen = set()
    while obj is not None:
        if obj.index in seen or obj.object_flags & 0x30 or obj.index in catalog.classes:
            return False
        seen.add(obj.index)
        obj = catalog.by_index.get(obj.outer_index)
    return True


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
        self.drafts = {}
        self.scaling = {}
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
        from expedition33.picto_baselines import Baselines
        self.baselines=Baselines(settings_dir() / 'picto-baselines.json')
        self.restore_error = None
        self.clear_confirm = None
        self.clear_message = ''
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
        self.owner_thread = threading.get_ident()
        self.main_reader = sdk_reader.ReadBatch(self.pid, share=True, _executable=self.reader_exe)
        self.worker_reader = None
        self.stats = {}
        self.multipliers = {}
        self.view_identity = None
        self.view_item = None
        self.character = None
        self.mode = "stat"
        self.level = None
        self.extra = {}
        self.lumina_ui_pending=False
        self.tools_page = False
        self.bulk_level = 33
        self.bulk_job = None
        self.bulk_message = 'Only currently owned Pictos'
        self.catalog_page = None
        self.native_catalog = None
        self.catalog_offset = 0
        self.catalog_selection = None
        self.ownership_drafts = {}
        self.ownership = None
        self.catalog_future = None
        self.catalog_request = None
        self.catalog_metadata = {}
        self.unlock_transaction = None
        self.unlock_bulk = None
        self.unlock_confirm = None
        self.unlock_reported = None
        from expedition33.picto_cards import PictoCardLayout
        self.card_layout = PictoCardLayout(self)

    @contextmanager
    def operation(self):
        active = sdk_reader.active_reader()
        if active is not None:
            with sdk_reader.ReadBatch(self.pid):
                yield
            return
        if threading.get_ident() == self.owner_thread:
            owner = self.main_reader
        else:
            if self.worker_reader is None:
                self.worker_reader = sdk_reader.ReadBatch(self.pid, share=True, _executable=self.reader_exe)
            owner = self.worker_reader
        try:
            with owner.bind():
                yield
        except RuntimeQueryError:
            # A failed native read permanently closes its batch. Discard the
            # observation worker on its own thread so the next poll can start
            # a new read-only operation, rather than reusing a dead reader.
            # Do not retry this operation or any owner-thread mutation.
            if threading.get_ident() != self.owner_thread:
                owner.close()
                self.worker_reader = None
                self.card_layout.pending = None
            raise

    def call(self, obj, owner, name, **args):
        # Setters return no identities; preserve the selector cache instead of
        # rebuilding its catalog after each text/stat update.
        started = time.perf_counter()
        try:
            with self.planner.prepare(obj, self.fn(owner, name), **args).invoke() as result:
                return result.return_value
        finally:
            self.measure('call.' + name, started)

    def measure(self, name, started):
        counts = self.timings.setdefault('operations', {})
        count, elapsed = counts.get(name, (0, 0))
        counts[name] = (count + 1, round(elapsed + (time.perf_counter() - started) * 1000, 2))

    def create(self, obj, owner, name, **args):
        started = time.perf_counter()
        try:
            return super().create(obj, owner, name, **args)
        finally:
            self.measure('create.' + name, started)

    def read_stats(self, item):
        values = self.project(self.planner._catalog, item, 'CurrentStats', 'BaseStatsMultipliers')
        return dict(field(values, 'CurrentStats').items), dict(field(values, 'BaseStatsMultipliers').items)

    def project(self, catalog, obj, *names):
        return self.map_values.read_values_many(catalog, (obj,), fields=names)[obj.index]

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
        started = time.perf_counter()
        found, catalog = self.map_values.read_object_reference(self.planner._catalog,
            obj, self.cls(owner), name, project=True)
        self.planner.adopt_observations(catalog)
        self.measure('reference', started)
        return found

    def observed_reference(self, values, obj, owner, name):
        key = (self.cls(owner).index, name)
        if key in values.values and key not in values.errors:
            return values.values[key]
        return self.reference(obj, owner, name)

    def discover(self):
        c = capture_matching(self.pid, names=(
            'WBP_BaseButton_C', 'CommonButtonBase', 'CommonActivatableWidget', 'CommonTextBlock', 'TextBlock',
            'TextLayoutWidget', 'Widget', 'UserWidget', 'GridPanel', 'GridSlot',
            'PanelSlot', 'ContentWidget', 'CanvasPanel', 'CanvasPanelSlot', 'Overlay', 'OverlaySlot', 'CTS_B1_SmallLine_Outline_C',
            'WidgetBlueprintLibrary', 'GameplayStatics', 'Default__WidgetBlueprintLibrary', 'Default__GameplayStatics', 'Create',
            'SpawnObject', 'SetContent', 'GetContent', 'AddChildToGrid', 'AddChildToCanvas', 'AddChildToOverlay',
            'SetPosition', 'SetSize', 'SetPadding', 'SetHorizontalAlignment', 'SetVerticalAlignment',
            'SetText', 'SetStyle', 'SetJustification', 'SetAutoWrapText', 'SetWrapTextWidth', 'SetMinDimensions', 'SetIsSelectable', 'SetIsToggleable',
            'RemoveFromParent', 'HandleButtonClicked', 'SetRenderTransformPivot', 'SetRenderScale', 'SetLayer',
            'SetIsEnabled', 'SetBaseStatsMultiplier', 'SetCurrentStatValue', 'RefreshCurrentGearStats', 'ChangeLevel', 'SetPassiveEffectSharedProgression',
            'RefreshUsedLuminaPointsInternal', 'UpdateEquipmentStats', 'RefreshSlotData', 'DT_PassiveEffects', 'DT_EquipmentScalingTable_Pictos', 'S_jRPG_Item_DynamicData',
            'S_jRPG_Item_StaticData', 'FPassiveEffect', 'FPassiveEffectProgression', 'FCharacterAssignedEquipment', 'FEquipmentSlot',
            'PointerToUberGraphFrame', 'S_GearScalingLevel', 'S_LootContext', 'Margin', 'Vector2D',
            'LinearColor', 'Anchors', 'WidgetTransform', 'EHorizontalAlignment', 'EVerticalAlignment', 'ETextJustify',
            'FormatArgumentData', 'EAttributeScalingGrade', 'ECharacterAttribute', 'EWeaponQuality',
            'BP_DataAsset_Skill_C', 'BP_PictoViewItem_C', 'WBP_GM_SkillElementShort_C', 'WBP_PictoSlot_C',
            'S_WeaponDefinition', 'S_WeaponInstanceHandle',
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
            'BP_CharacterData_C', 'BP_jRPG_GI_Custom_C', 'BP_ItemUpgradeSystem_C'))
        from expedition33.picto_inventory import owned_pictos
        return owned_pictos(self.pid, catalog=c)[0]

    def progression_catalog(self):
        """Fresh progression dependencies; never enumerate transient passives/UI."""
        return capture_matching(self.pid, names=(
            'DT_PassiveEffects', 'ChangeLevel', 'LoadCharacter', 'SetPassiveEffectSharedProgression',
            'RefreshUsedLuminaPointsInternal', 'UpdateEquipmentStats',
            'SetBaseStatsMultiplier', 'SetCurrentStatValue', 'RefreshCurrentGearStats', 'Map_Remove',
            'FPassiveEffect', 'FPassiveEffectProgression', 'E_jRPG_StatType',
            'S_GearScalingLevel', 'S_LootContext', 'FormatArgumentData',
            'EAttributeScalingGrade', 'ECharacterAttribute', 'EWeaponQuality',
            'BP_DataAsset_Skill_C', 'BP_PictoViewItem_C', 'WBP_GM_SkillElementShort_C',
            'WBP_PictoSlot_C', 'S_WeaponDefinition', 'S_WeaponInstanceHandle',
            'FEquipmentSlot', 'S_jRPG_Item_DynamicData', 'S_jRPG_Item_StaticData'),
            classes=('BP_ItemUpgradeSystem_C', 'BP_CharacterData_C', 'BP_jRPG_GI_Custom_C'))

    def install(self):
        started = time.perf_counter()
        with self.operation():
            try:
                c = getattr(self, 'warm_catalog', None)
                if c is None:
                    c = self.discover()
                self.warm_catalog = None
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
            # Class widget-tree templates are not runtime menu instances.
            # Resolve the actual panel only after the character menu opens.
            self.panel = None
            self.player = self.one(o for o in c.select('PlayerController')
                if not o.object_flags & 0x30 and any(k[1] == 'Player' and
                    getattr(v, 'class_name', '') == 'LocalPlayer'
                    for k, v in self.map_values.read_values(c, o).values.items()))
            self.game_instance = self.one(o for o in c.select('BP_jRPG_GI_Custom_C') if not o.object_flags & 0x30)
            self.passive_table = self.one(o for o in c.objects if o.class_name=='DataTable' and c.path_name(o)=='/Game/Gameplay/Lumina/DT_PassiveEffects.DT_PassiveEffects')
            table = self.one(o for o in c.objects if o.class_name=='DataTable' and c.path_name(o)==
                '/Game/Gameplay/Pictos/DT_EquipmentScalingTable_Pictos.DT_EquipmentScalingTable_Pictos')
            for name, row in self.map_values.read_table_rows(c, table).items():
                level = field(row, 'Level_2_90763A154CD780355ABBC89C3E42BD18')
                if name != f'Level_{level}' or level in self.scaling:
                    raise RuntimeError('Picto scaling row identity mismatch')
                self.scaling[level] = dict(field(row, 'Stats_19_14AC0B3B43D586575C5433A630321A61').items)
            if not set(range(1,34)) <= self.scaling.keys():
                raise RuntimeError('Incomplete Picto scaling table')
            self.passives = {}
            # Resolve passive instances lazily after the menu is visible.
            self.view_catalog = c
            keep = {self.player.index, *([self.panel.index] if self.panel else []), *(v.index for v in self.inventory_candidates)}
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
            self.defer_layout(self.root, 'CommonButtonBase', 'SetIsSelectable', bInIsSelectable=False)
            self.defer_layout(self.root, 'CommonButtonBase', 'SetIsToggleable', bInIsToggleable=False)
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
            self.value_label = self.make_label('Select a field', 12, 186, 280, 35)
            self.status_label = self.make_label('Draft changes; Apply to commit', 12, 222, 395, 35)
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
            _, self.tools_label = self.make_button(library, 'All Pictos', 425, 222, 165, 35)
            _, self.ownership_label = self.make_button(library, 'Unlock status', 300, 186, 285, 32)
            _, self.clear_label = self.make_button(library, 'Clear all saved changes', 12, 260, 578, 32)
            self.flush_layout()
            self.defer_layout(self.root, 'CommonButtonBase', 'SetMinDimensions', InMinWidth=610, InMinHeight=302)
            self.defer_layout(self.root, 'Widget', 'SetRenderTransformPivot', Pivot={'X':0., 'Y':0.})
            self.defer_layout(self.root, 'Widget', 'SetRenderScale', Scale={'X':.8, 'Y':.8})
            self.writes_available = getattr(self.scope._session._transport, 'picto_edit_protocol', 0) == 1
            self.defer_layout(self.buttons[6], 'Widget', 'SetIsEnabled', bInIsEnabled=self.writes_available)
            self.progression_available = getattr(self.scope._session._transport, 'picto_progression_protocol', 0)==1
            for button in (self.level_button, self.mastery_button):
                self.defer_layout(button, 'Widget', 'SetIsEnabled', bInIsEnabled=self.progression_available)
            self.cost_available=getattr(self.scope._session._transport,'picto_cost_protocol',0)==1
            self.defer_layout(self.cost_button,'Widget','SetIsEnabled',bInIsEnabled=self.cost_available)
            self.flush_layout()
            self.ui_planner = self.scope.invocation_planner(selected_results=True, catalog=self.planner._catalog)
            self.ui_planner.prepare(self.header, self.fn('TextBlock', 'SetText'), InText='PICTO EDITOR')
            self.timings['widgets_ms'] = round((time.perf_counter() - stage) * 1000, 1)
            self.timings['attach_ms'] = round((time.perf_counter() - started) * 1000, 1)
            self.error = None
            self.state = 'warm'
            self._renew_at = time.monotonic() + 120
            log.info('Picto editor controls prewarmed; timings=%s', self.timings)
            return True

    def attach_warm(self):
        if self.panel is None:
            values = self.map_values.read_values_many(self.planner._catalog, (self.player,),
                fields=('IsGameMenuVisible',))[self.player.index]
            if not field(values, 'IsGameMenuVisible'):
                return False
            fresh = capture_matching(self.pid, classes=('WBP_Panel_Pictos_C',))
            panels = [o for o in fresh.select('WBP_Panel_Pictos_C') if runtime_widget(fresh, o)]
            if not panels:
                return False
            self.panel = self.one(panels)
            self.planner.adopt_observations(fresh)
        tree = self.reference(self.panel, 'UserWidget', 'WidgetTree')
        if tree is None:
            return False
        self.host = self.reference(tree, 'WidgetTree', 'RootWidget')
        if self.host is None:
            return False
        if self.host.class_name == 'SafeZone':
            self.host = self.create(self.host, 'ContentWidget', 'GetContent')
        if self.host.class_name != 'GridPanel':
            raise RuntimeError('Stock Picto root is not the verified GridPanel: ' + self.host.class_name)
        slot = self.create(self.host, 'GridPanel', 'AddChildToGrid', Content=self.root, InRow=0, InColumn=0)
        self.call(slot, 'GridSlot', 'SetPadding', InPadding={'Left':770., 'Top':60., 'Right':0., 'Bottom':0.})
        self.call(slot, 'GridSlot', 'SetHorizontalAlignment', InHorizontalAlignment=1)
        self.call(slot, 'GridSlot', 'SetVerticalAlignment', InVerticalAlignment=1)
        self.call(slot, 'GridSlot', 'SetLayer', InLayer=100)
        self.state = 'attached'
        log.info('Picto warm editor attached to panel %s', self.panel.index)
        return True

    def defer_layout(self, obj, owner, name, **args):
        if (not _ui_batch.layout_available(self.scope._session) or
            (name in _ui_batch.EXTENDED_LAYOUT_SETTERS and not _ui_batch.extended_layout_available(self.scope._session))):
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
        self.defer_layout(button, 'CommonButtonBase', 'SetMinDimensions', InMinWidth=width, InMinHeight=height)
        content = self.reference(button, 'WBP_BaseButton_C', 'ButtonContent')
        text = self.spawn('CommonTextBlock')
        self.defer_layout(text, 'CommonTextBlock', 'SetStyle', InStyle=self.style)
        self.defer_layout(text, 'TextLayoutWidget', 'SetJustification', InJustification=1)
        self.flush_layout()
        self.call(text, 'TextBlock', 'SetAutoWrapText', InAutoTextWrap=True)
        self.call(text, 'CommonTextBlock', 'SetWrapTextWidth', InWrapTextAt=int(width-20))
        self.defer_layout(text, 'TextBlock', 'SetText', InText=title)
        frame = self.spawn('Overlay')
        text_slot = self.create(frame, 'Overlay', 'AddChildToOverlay', Content=text)
        # Give wrapped text the full row width; centering its desired width
        # before it has text otherwise collapses the available wrap area.
        self.defer_layout(text_slot, 'OverlaySlot', 'SetHorizontalAlignment', InHorizontalAlignment=0)
        self.defer_layout(text_slot, 'OverlaySlot', 'SetVerticalAlignment', InVerticalAlignment=2)
        self.call(content, 'ContentWidget', 'SetContent', Content=frame)
        slot = self.place(self.canvas, button, x, y, width, height)
        if not hasattr(self,'button_slots'):self.button_slots={}
        self.button_slots[button.index]=slot
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
        return slot

    def make_label(self, text, x, y, w, h):
        label = self.spawn('CommonTextBlock')
        self.defer_layout(label, 'CommonTextBlock', 'SetStyle', InStyle=self.style)
        self.defer_layout(label, 'TextBlock', 'SetText', InText=text)
        self.place(self.canvas, label, x, y, w, h)
        return label

    def text(self, label, value):
        if self._text.get(label.index) != value:
            if getattr(self, '_paint_batch', None) is not None:
                self._paint_batch[label.index] = (label, value)
                return
            planner = self.ui_planner or self.planner
            with planner.prepare(label, self.fn('TextBlock', 'SetText'), InText=value).invoke() as result:
                pass
            self._text[label.index] = value

    def observe(self, catalog, view_catalog, catalog_identity=False):
        # Read-only worker thread: owns its short-lived native reader and local
        # catalogues. It never invokes UFunctions or changes session resources.
        started = time.perf_counter()
        with self.operation():
            values = self.project(catalog, self.panel, 'bIsActive', 'CurrentCharacterData',
                'FocusedItem', 'SelectedPictoViewItem', 'FocusedSlot')
            if not field(values, 'bIsActive'):
                return catalog, view_catalog, None, None, None, {}, time.perf_counter() - started
            if catalog_identity is False:self.card_layout.observe(catalog)
            def ref(obj, owner, name, observed=None):
                nonlocal catalog
                key = (catalog.find_class(owner).index, name)
                if observed is not None and key in observed.values and key not in observed.errors:
                    return observed.values[key]
                value, catalog = self.map_values.read_object_reference(catalog, obj,
                    catalog.by_index[catalog.find_class(owner).index], name, project=True)
                return value
            if not self.inventory_ready:
                from expedition33.picto_inventory import owned_pictos
                # View objects are recycled whenever the native list rebuilds.
                # Inventory membership must not depend on merging those slots.
                _,owned=owned_pictos(self.pid)
                self.inventory = {identity:item for identity,(item,_) in owned.items()}
                self.inventory_ready = True
            character = ref(self.panel, 'WBP_Panel_Pictos_C', 'CurrentCharacterData', values)
            if catalog_identity is not False:
                identity = catalog_identity
                if identity not in self.inventory:
                    return catalog, view_catalog, character, None, None, {'catalog_identity':identity}, time.perf_counter()-started
            else:
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
                view_values, view_catalog = self.map_values.read_values_with_references(view_catalog, view, fields=('ItemDynamicData',))
                dynamic = field(view_values, 'ItemDynamicData')
                static = dynamic.fields['ItemStaticData_9_59CF465348F5D7696BDFE68CB4071486']
                identity = static.fields['Item_HardcodedName_90_C7F763B74AAB28EF890A66854D7D95AA']
            item = self.inventory.get(identity)
            if item is None or item.class_name != 'BP_ItemInstance_Gear_Pictos_C':
                raise RuntimeError('No exact owned Picto for selection')
            if not same_object(catalog.by_index.get(item.index),item):
                fresh=capture_selected(self.pid,((item.index,item.serial,item.address),))
                catalog=catalog.with_observations(fresh)
            values = self.project(catalog, item, 'ItemDefinitionID', 'CurrentLevel', 'CurrentStats', 'BaseStatsMultipliers')
            shared = field(self.project(view_catalog,self.game_instance, 'SharedPassiveEffectProgression'), 'SharedPassiveEffectProgression').items
            progression = shared.get(identity)
            extra = {'mastered':progression.fields['IsLearnt_9_2561000E49D90653437DE9A45BE2A86D'] if progression else False}
            passive = self.passives.get((character.index, identity)) if character else None
            if passive is None and character is not None:
                fresh=capture_matching(self.pid,classes=('BP_PassiveEffectInstance_C','BP_CharacterData_C'))
                # Menu reload recycles view/passive objects. This read-only
                # snapshot has no owned widgets: replace it rather than merge
                # new UObject identities into stale runtime slots.
                retained=view_catalog.subset(o for o in view_catalog.objects if
                    o.index in view_catalog.classes or o.class_name in ('Function','Enum','UserDefinedEnum','ScriptStruct','UserDefinedStruct') or same_object(o,self.game_instance))
                view_catalog=retained.with_observations(fresh)
                candidates = tuple(obj for obj in fresh.select('BP_PassiveEffectInstance_C') if not obj.object_flags & 0x30)
                identities = self.map_values.read_values_many(view_catalog, candidates, fields=('OwnerData', 'PassiveEffectID'))
                for obj in candidates:
                    observed=identities[obj.index]
                    owner=field(observed,'OwnerData')
                    if owner is not None:self.passives[(owner.index,field(observed,'PassiveEffectID'))]=obj
                passive=self.passives.get((character.index,identity))
            if passive is not None:
                pv = self.project(view_catalog, passive, 'OwnerData', 'PassiveEffectID', 'PassiveDefinition')
                if not same_object(field(pv,'OwnerData'),character) or field(pv,'PassiveEffectID') != identity:
                    raise RuntimeError('Passive definition selection changed')
                definition = field(pv,'PassiveDefinition').fields
                shared = field(self.project(view_catalog,self.game_instance, 'SharedPassiveEffectProgression'), 'SharedPassiveEffectProgression').items
                progression = shared.get(identity)
                extra = {'source':passive, 'cost':definition['LuminaCost_15_BC10A93D48987A14F96279AC521E94CF'],
                    'threshold':definition['LuminaUnlockStepsCount_19_B80447FF455A4D693EAD2991AD473004'],
                    'steps':progression.fields['LearntSteps_6_A14D681549E830249C77BD95F2B4CF3F'] if progression else 0,
                    'mastered':progression.fields['IsLearnt_9_2561000E49D90653437DE9A45BE2A86D'] if progression else False}
            if catalog_identity is not False:extra['catalog_identity']=catalog_identity
            return catalog, view_catalog, character, item, values, extra, time.perf_counter() - started

    def accept_observation(self, result):
        if self.catalog_page and result[5].get('catalog_identity',False) != self.catalog_selection:
            return  # A selection changed while its read was in flight.
        catalog, self.view_catalog, character, item, values, self.extra, elapsed = result
        # Merge into the owner thread's current catalogue, preserving owned widgets.
        self.planner.adopt_observations(catalog)
        self.card_layout.apply()
        self.selection = item
        self.character = character
        self.timings['refresh_ms'] = round(elapsed * 1000, 1)
        if item is None:
            self.definition_id=self.catalog_selection if self.catalog_page else None
            if self.tools_page or getattr(self,'catalog_page',None):
                self.paint_value();return
            self.text(self.value_label, 'Select a Picto')
            for button, text, name in self.stat_rows.values():
                self.text(text, name + ': --')
            return
        self.definition_id = field(values, 'ItemDefinitionID')
        self.level = field(values, 'CurrentLevel')
        self.stats = dict(field(values, 'CurrentStats').items)
        self.multipliers = dict(field(values, 'BaseStatsMultipliers').items)
        self.paint_value()

    def draft(self):
        identity = (self.selection.pid, self.selection.index, self.selection.serial, self.selection.address)
        draft = self.drafts.get(self.definition_id)
        if draft is None or draft.identity != identity:
            draft = self.drafts[self.definition_id] = PictoDraft(identity)
        return draft

    def current_fields(self):
        return {**{('stat', key): value for key,value in self.multipliers.items()},
            ('level', None): self.level, ('cost', None): self.extra.get('cost'),
            ('mastery', None): self.extra.get('mastered')}

    def refresh_current(self):
        # Apply requires a fresh observation; discard older background work.
        if self.refresh_future is not None:
            self.refresh_future.result()
            self.refresh_future = None
        self.accept_observation(self.observe(self.planner._catalog, self.view_catalog,
            self.catalog_selection if self.catalog_page else False))

    def paint_value(self):
        if getattr(self,'catalog_page',None) and hasattr(self,'buttons'):
            enabled=self.selection is not None
            if getattr(self,'_editor_enabled',None)!=enabled:
                for button in self.buttons[:10]:self.defer_layout(button,'Widget','SetIsEnabled',bInIsEnabled=enabled)
                self.flush_layout()
                self._editor_enabled=enabled
        elif getattr(self,'_editor_enabled',True) is False:
            for button in self.buttons[:10]:self.defer_layout(button,'Widget','SetIsEnabled',bInIsEnabled=True)
            self.flush_layout();self._editor_enabled=True
        if not hasattr(self, 'ui_planner') or not _ui_batch.available(self.scope._session):
            return self._paint_value()
        self._paint_batch = {}
        try:
            self._paint_value()
            updates = tuple(self._paint_batch.values())
        finally:
            self._paint_batch = None
        planner = self.ui_planner or self.planner
        _ui_batch.invoke_setters(self.scope, [planner.prepare(label, self.fn('TextBlock', 'SetText'), InText=value)
            for label, value in updates])
        self._text.update({label.index: value for label, value in updates})

    def _paint_value(self):
        if hasattr(self,'clear_label'):
            target='all' if self.tools_page else self.definition_id
            pending=getattr(self,'clear_confirm',None)
            confirming=pending is not None and pending==(self.tools_page,target)
            self.text(self.clear_label, 'Confirm: restore baseline' if confirming else 'Clear Picto Changes' if self.tools_page else 'Clear all saved changes')
        if getattr(self, 'catalog_page', None):
            self.paint_catalog()
        if self.tools_page:
            self.text(self.header, 'PICTO TOOLS | Gameplay Pictos')
            removing=self.unlock_confirm is not None and not getattr(self,'unlock_confirm_desired',True)
            for key,title in zip(self.stat_rows, (f'Target level: {self.bulk_level}', 'Browse Pictos', 'EXPERIMENTAL',
                    f'Remove {self.unlock_confirm}?' if removing else 'Remove All')):
                self.text(self.stat_rows[key][1], title)
            self.text(self.level_label, 'Mass level all Pictos')
            self.text(self.mastery_label, 'Master all Pictos')
            self.text(self.cost_label, 'Confirm: add '+str(self.unlock_confirm) if self.unlock_confirm is not None and not removing else 'Unlock All Missing')
            if hasattr(self,'ownership_label'):self.text(self.ownership_label,'Unmaster all Pictos')
            for label,title in zip(self.adjust_labels, ('- 1','+ 1','Cancel')):
                self.text(label,title)
            job=self.bulk_job
            self.text(self.value_label, f'{job.mode.title()}: {job.completed} / {job.total}' if job else f'Owned target: Lv {self.bulk_level}')
            self.text(self.status_label,getattr(self,'clear_message','') or self.bulk_message)
            self.text(self.tools_label,'Editor')
            return
        if hasattr(self,'tools_label'):
            self.text(self.tools_label,'Tools')
        if hasattr(self,'ownership_label'):
            pending=self.ownership_drafts.get(self.definition_id) if self.catalog_page else None
            self.text(self.ownership_label,('Remove *' if pending else 'Remove Picto…') if self.catalog_page and self.selection is not None else 'Unlock status: Owned' if self.selection is not None else 'Browse unlock status')
        if self.selection is None:
            if self.catalog_page:
                name=self.ownership.rows.get(self.catalog_selection,{}).get('name','Select a Picto')
                self.text(self.header,'PICTO EDITOR | '+name)
                for _,label,title in self.stat_rows.values():self.text(label,title+': —')
                for label,title in ((self.level_label,'Level'),(self.mastery_label,'Mastery'),(self.cost_label,'Lumina cost')):
                    self.text(label,title+': —')
                self.text(self.value_label,'Locked — unlock below')
                self.text(self.status_label,'Existing drafts retained')
                for label,title in zip(self.adjust_labels,('-','+','Apply')):self.text(label,title)
            return
        draft = self.draft()
        fields = self.current_fields()
        level = draft.value(('level', None), self.level)
        multipliers = {key: draft.value(('stat', key), value) for key,value in self.multipliers.items()}
        projected = preview_stats(self.scaling, level, multipliers)
        display_name=self.ownership.rows.get(self.definition_id,{}).get('name',self.definition_id) if self.ownership is not None else self.definition_id
        self.text(self.header, 'PICTO EDITOR | ' + display_name + (' *' if draft.changes else '') + f' | Lv {level}')
        for key, (button, text, name) in self.stat_rows.items():
            marker = '> ' if self.mode == 'stat' and key == self.stat_key else ''
            dirty = ('stat', key) in draft.changes or ('level', None) in draft.changes
            value = projected[key] if dirty else self.stats.get(key, 0)
            suffix = ('%' if key == 9 else '') + ('*' if dirty else '')
            self.text(text, f'{marker}{name}: {value:g}{suffix}')
        def row(label, mode, title, value):
            self.text(label, ('> ' if self.mode == mode else '') + title + str(value) + ('*' if (mode,None) in draft.changes else ''))
        row(self.level_label, 'level', 'Level: ', level)
        row(self.mastery_label, 'mastery', 'Mastery: ', ('Mastered' if draft.value(('mastery',None),self.extra.get('mastered')) else 'Unmastered') if 'mastered' in self.extra else '—')
        row(self.cost_label, 'cost', 'Lumina cost: ', draft.value(('cost',None),self.extra.get('cost',self.catalog_metadata.get(self.definition_id,{}).get('cost','—'))))
        if self.mode == 'stat':
            name = self.stat_rows[self.stat_key][2]
            value = projected[self.stat_key]
            label = f'{name}: {value:g}' + ('%' if self.stat_key == 9 else '')
            minus,plus = '- 0.1','+ 0.1'
        elif self.mode == 'level':
            label = f'Picto level: {level}'; minus,plus = '- 1','+ 1'
        elif self.mode == 'cost':
            label = 'Lumina cost (shared)'; minus,plus = '- 1','+ 1'
        else:
            label = 'Lumina mastery'; minus,plus = 'Reset','Master'
        self.text(self.value_label, label)
        self.text(self.adjust_labels[0],minus); self.text(self.adjust_labels[1],plus)
        self.text(self.adjust_labels[2], 'Apply')
        count=len(draft.changes)
        # Choose once before queuing text: a second write can be skipped against
        # the previous frame's cache, leaving the first message to flicker.
        status = ('Removal pending — select Apply' if self.definition_id in self.ownership_drafts
                  else f'{count} pending edit' + ('s' if count != 1 else '') + ' — select Apply' if count
                  else '')
        self.text(self.status_label, getattr(self, 'clear_message', '') or status)

    def clear_saved_changes(self):
        # A running operation may still persist its confirmed results.
        if self.bulk_job is not None or self.unlock_bulk is not None or (self.unlock_transaction and self.unlock_transaction.busy):
            self.clear_message='Wait for the current operation'
            self.paint_value();self.text(self.status_label,self.clear_message);return
        identity=self.definition_id
        if not self.tools_page and not identity:return
        target=(self.tools_page,'all' if self.tools_page else identity)
        if getattr(self,'clear_confirm',None)!=target:
            self.clear_confirm=target
            self.clear_message='Select Confirm to restore starting values'
        else:
            from expedition33.picto_saved_changes import clear_saved
            identities=tuple(self.preferences.profiles) if self.tools_page else (identity,)
            try:targets=self.baselines.targets(self.pid,identities)
            except RuntimeError as error:
                self.clear_confirm=None;self.clear_message=str(error)
                self.paint_value();self.text(self.status_label,self.clear_message);return
            from expedition33.picto_restore import restore
            with self.operation():
                result=restore(self.scope,targets,catalog=self.progression_catalog())
                if result['missing']:raise RuntimeError('Baseline restore incomplete; overrides retained')
                if self.ownership is None:
                    from expedition33.picto_inventory import PictoOwnership
                    self.ownership=PictoOwnership(self.scope)
                if self.ownership is not None:
                    character=self.reference(self.panel,'WBP_Panel_Pictos_C','CurrentCharacterData') if self.panel else None
                    if character is not None:self.ownership.refresh_panel(self.panel,character)
            clear_saved(self.preferences,None if self.tools_page else identity)
            self.refresh_current()
            self.lumina_ui_pending=True
            # Only discard pending state after the atomic settings write succeeds.
            if self.tools_page:
                self.restore_queue.clear();self.drafts.clear();self.ownership_drafts.clear()
            else:
                self.restore_queue=[entry for entry in self.restore_queue if entry[0]!=identity]
                self.drafts.pop(identity,None);self.ownership_drafts.pop(identity,None)
            if not self.restore_queue:self.restore_error=None
            self.clear_confirm=None
            self.clear_message='Starting values restored'
        self.paint_value()
        self.text(self.status_label,self.clear_message)

    def submit_read(self, callback):
        def run():
            with self.operation():return callback()
        return self.refresh_worker.submit(run)

    def prepare_catalog(self):
        if self.ownership is not None or self.catalog_future is not None:return
        def read():
            from expedition33.picto_inventory import prepare_ownership
            from expedition33.picto_details import definition_details, METADATA_NAMES
            from expedition33.picto_catalog import prepare_metadata
            started=time.perf_counter()
            ownership=prepare_ownership(self.pid)
            metadata={}
            try:
                fresh=capture_matching(self.pid,names=METADATA_NAMES)
                ownership['catalog']=ownership['catalog'].with_observations(fresh)
                metadata=definition_details(ownership['catalog'],ownership['rows'])
            except Exception as error:
                log.warning('Picto definition details unavailable: %s',error)
            return ownership,metadata,prepare_metadata(self.pid),time.perf_counter()-started
        self.catalog_future=self.submit_read(read)

    def open_catalog(self, section, selected=None):
        self.catalog_request=(section,selected)
        self.catalog_open_started=time.perf_counter()
        if self.ownership is None:
            self.prepare_catalog()
            self.text(self.status_label,'Loading catalog… editor remains available')
            return
        if self.native_catalog is not None and self.native_catalog.build_ready:self.show_catalog()
        else:self.text(self.status_label,'Preparing catalog controls… editor remains available')

    def show_catalog(self):
        from expedition33.picto_catalog import CatalogView,NativeCatalog
        section,selected=self.catalog_request
        self.catalog_request=None
        self.catalog_page=section
        self.tools_page=False
        self.catalog_view=CatalogView(self.ownership.rows,self.ownership.owned,experimental=section=='experimental')
        self.catalog_selection=selected if selected in self.catalog_view.ids else next(iter(self.catalog_view.ids),None)
        self.inventory={key:item for key,(item,_) in self.ownership.owned.items()}
        self.inventory_ready=True
        self.view_catalog=self.view_catalog.with_observations(self.ownership.catalog)
        if self.native_catalog is None:self.native_catalog=NativeCatalog(self)
        self.native_catalog.metadata=self.catalog_ui_metadata
        self.native_catalog.show(self.catalog_view)
        self.select_catalog(self.catalog_selection)
        self.timings['catalog_open_ms']=round((time.perf_counter()-self.catalog_open_started)*1000,2)
        log.info('Picto catalog opened: %s',self.timings)

    def select_catalog(self, identity):
        # Drafts remain keyed by definition + inventory identity. No draft is
        # committed or moved when the selected catalog record changes.
        self.catalog_selection=identity
        self.definition_id=identity
        self.selection=None
        self.extra={}
        self.stats={};self.multipliers={};self.level=None
        self.next_scan=0
        self.paint_value()

    def paint_catalog(self):
        identity=self.catalog_selection
        row=self.ownership.rows.get(identity,{})
        data=dict(self.catalog_metadata.get(identity,{}))
        data.update(identity=identity,name=row.get('name'),normal=row.get('normal',False),owned=identity in self.ownership.owned)
        if self.selection is not None and self.definition_id==identity:
            data.update(level=self.level,mastery=('Mastered' if self.extra['mastered'] else 'Unmastered') if 'mastered' in self.extra else None,
                health=self.stats.get(1,0),defense=self.stats.get(6,0),speed=self.stats.get(8,0),critical_rate=str(self.stats.get(9,0))+'%')
            if 'cost' in self.extra:data['cost']=self.extra['cost']
        tx=self.unlock_transaction
        if tx is not None and tx.identity==identity:data.update(state=tx.state,message=tx.error)
        elif tx is not None and tx.identity is not None:
            data.update(state=tx.state,message=self.ownership.rows[tx.identity]['name']+(' — '+tx.error if tx.error else ''))
        if getattr(self,'catalog_action_error',(None,None))[0]==identity:
            data.update(state='Failed',message=self.catalog_action_error[1])
        self.native_catalog.update_details(data)

    def ownership_ui_refresh(self):
        # The transaction already re-read authoritative inventory on its worker.
        self.inventory={key:item for key,(item,_) in self.ownership.owned.items()}
        self.inventory_candidates=tuple(self.inventory.values());self.inventory_ready=True
        self.view_catalog=self.view_catalog.with_observations(self.ownership.catalog)
        self.passives={}
        if self.catalog_page:
            previous=self.catalog_selection
            self.catalog_view.owned=dict(self.ownership.owned)
            self.native_catalog.reset()
            self.select_catalog(self.catalog_selection)

    def start_unlock(self, identity):
        from expedition33.picto_transactions import UnlockTransaction
        if self.unlock_bulk is not None:return
        if self.unlock_transaction is None or not self.unlock_transaction.desired:
            self.unlock_transaction=UnlockTransaction(self.ownership,self.submit_read)
        if self.unlock_transaction.start(identity):
            self.unlock_reported=None
            self.paint_value()

    def poll_unlock(self):
        if self.unlock_bulk is not None and getattr(self.unlock_bulk,'native',False) is True:
            job=self.unlock_bulk;job.poll()
            self.bulk_message=f'Processed {job.processed} / {job.total}'
            if job.done:
                level=getattr(job,'level',None);mastery=getattr(job,'mastery',None)
                if level:
                    self.preferences.remember_field(job.completed+job.skipped,'level',level[0])
                    fresh=self.progression_catalog()
                    planner=self.scope.invocation_planner(selected_results=True,catalog=fresh)
                    cls=fresh.find_class('BP_CharacterData_C')
                    fn=self.one(o for o in fresh.objects if o.outer_index==cls.index and o.name=='UpdateEquipmentStats')
                    for character in fresh.select('BP_CharacterData_C'):
                        if not character.object_flags&0x30:
                            with planner.prepare(character,fn).invoke():pass
                    for identity in job.completed+job.skipped:
                        draft=self.drafts.get(identity)
                        if draft is not None:draft.acknowledge(('level',None))
                elif mastery is not None:
                    self.preferences.remember_field(job.completed+job.skipped,'mastered',mastery[0])
                    for identity in job.completed+job.skipped:
                        draft=self.drafts.get(identity)
                        if draft is not None:draft.acknowledge(('mastery',None))
                    self.lumina_ui_pending=True
                else:self.preferences.remember_ownership(job.completed+job.skipped,job.transaction.desired)
                self.ownership.owned=dict(job.transaction.owned)
                if job.transaction.desired and not level and mastery is None:
                    profiles={key:{k:v for k,v in self.preferences.profiles.get(key,{}).items() if k!='owned'} for key in job.completed}
                    profiles={key:value for key,value in profiles.items() if value}
                    if profiles:
                        from expedition33.picto_restore import restore
                        try:restore(self.scope,profiles,catalog=self.progression_catalog())
                        except Exception:log.exception('Bulk Picto overrides could not be fully restored')
                if self.panel is not None:
                    try:
                        character=self.reference(self.panel,'WBP_Panel_Pictos_C','CurrentCharacterData')
                        if character is not None:self.ownership.refresh_panel(self.panel,character)
                    except Exception:log.exception('Bulk Picto stock panel refresh failed')
                self.ownership_ui_refresh()
                elapsed=max(0.,job.clock()-job.started)
                self.bulk_message=f'Done {len(job.completed)} | Skip {len(job.skipped)} | Fail {len(job.failed)}'
                if job.error:self.bulk_message='Batch stopped; see diagnostics'
                log.info('Picto frame batch desired=%s elapsed_ms=%.2f completed=%s failed=%s frames=%s error=%s',
                    ('level:'+str(level[0])) if level else ('mastery:'+str(mastery[0])) if mastery is not None else job.transaction.desired,elapsed*1000,job.completed,job.failed,job.frames,job.error)
                self.unlock_bulk=None
            self.paint_value()
            return
        tx=self.unlock_transaction
        if tx is None:return
        # A failed preferences write must be resolved before bulk can advance
        # to another identity. Retrying a local save never retries the mutation.
        successful=('Unlocked','Already Owned','Removed','Already Absent')
        if not tx.busy and tx.identity is not None and self.unlock_reported != (tx.identity,tx.state) and tx.state in successful:
            self.preferences.remember(tx.identity,'owned',tx.desired)
        if self.unlock_bulk is not None:
            job=self.unlock_bulk
            job.poll()
            self.bulk_message=f'Done {len(job.completed)} | Skip {len(job.skipped)} | Fail {len(job.failed)}'
            if job.done:
                elapsed=max(0.,job.clock()-job.started)
                self.timings['bulk_elapsed_ms']=round(elapsed*1000,2)
                log.info('Picto bulk %s: %s; elapsed_ms=%.2f completed_per_second=%.3f completed=%s failed=%s error=%s',
                    'unlock' if tx.desired else 'remove',self.bulk_message,elapsed*1000,
                    len(job.completed)/elapsed if elapsed else 0.,job.completed,job.failed,job.error)
                self.unlock_bulk=None
        else:tx.poll()
        if not tx.busy and tx.identity is not None and self.unlock_reported != (tx.identity,tx.state):
            self.ownership.owned=dict(tx.owned)
            if tx.state in successful:
                self.preferences.remember(tx.identity,'owned',tx.desired)
            self.unlock_reported=(tx.identity,tx.state)
            if tx.state in successful:
                saved={k:v for k,v in self.preferences.profiles.get(tx.identity,{}).items() if k!='owned'}
                if tx.state=='Unlocked' and saved:
                    from expedition33.picto_restore import restore
                    try:restore(self.scope,{tx.identity:saved},catalog=self.progression_catalog())
                    except Exception:log.exception('Unlocked Picto profile restore failed; ownership retained')
                if self.panel is not None and self.character is not None:
                    try:self.ownership.refresh_panel(self.panel,self.character)
                    except Exception:log.exception('Picto stock panel refresh failed; confirmed ownership retained')
            self.ownership_ui_refresh()
            log.info('Picto ownership %s: %s error=%s timings=%s',tx.identity,tx.state,tx.error,tx.timings)
            self.paint_value()

    def activate_catalog(self,index):
        started=time.perf_counter()
        action=self.native_catalog.actions.get(index)
        if action and action.startswith('filter:'):
            kind=action.split(':',1)[1]
            self.catalog_view.experimental=kind=='experimental'
            self.catalog_page='experimental' if kind=='experimental' else 'normal'
            self.catalog_view.filter='all' if kind=='experimental' else kind
            self.native_catalog.reset()
            self.select_catalog(self.catalog_selection)
            self.timings['catalog_filter_ms']=round((time.perf_counter()-started)*1000,2)
        elif action=='unlock':self.start_unlock(self.catalog_selection)
        elif action=='tools':
            self.native_catalog.hide();self.catalog_page=None;self.tools_page=True;self.paint_value()
        elif index in self.native_catalog.mapping:
            self.select_catalog(self.native_catalog.mapping[index])
            self.native_catalog.poll()
            self.timings['catalog_select_ms']=round((time.perf_counter()-started)*1000,2)
        log.info('Picto catalog action %s selection=%s timings=%s',action or 'select',self.catalog_selection,
            {k:v for k,v in self.timings.items() if k.startswith('catalog_')})

    def activate(self,index):
        started = time.perf_counter()
        if index == 10:
            if getattr(self,'catalog_page',None):
                self.native_catalog.hide()
                self.catalog_page=None;self.tools_page=True;self.paint_value();return
            self.tools_page = not self.tools_page
            self.paint_value()
            return
        if index==12:
            self.clear_saved_changes();return
        self.clear_confirm=None
        self.clear_message=''
        if getattr(self,'catalog_page',None) and index >= 13:
            self.activate_catalog(index);return
        if self.unlock_bulk is not None:
            # Browsing stays available, but only one ownership/property batch
            # may mutate inventory. Cancel lets an in-flight readback finish.
            allowed=(1,2,6) if self.tools_page else (11,)
            if index not in allowed:return
        if self.tools_page:
            if self.bulk_job is not None:
                if index==6:
                    self.bulk_job.queue.clear()
                    self.bulk_message='Stopping after confirmed edits'
                return
            if index in (4,5):
                self.bulk_level=max(1,min(33,self.bulk_level+(-1 if index==4 else 1)))
            elif index in (1,2):
                self.open_catalog('normal' if index==1 else 'experimental');return
            elif index in (3,9):
                from expedition33.picto_transactions import UnlockTransaction,BulkUnlockTransaction
                desired=index==9
                if self.ownership is None:
                    self.prepare_catalog();self.bulk_message='Loading inventory; select again'
                elif self.unlock_confirm is None or getattr(self,'unlock_confirm_desired',True)!=desired:
                    self.unlock_confirm_desired=desired
                    self.unlock_confirm=sum(row['normal'] and ((key in self.ownership.owned)!=desired) for key,row in self.ownership.rows.items())
                    self.bulk_message=f'{"Add" if desired else "Remove"} {self.unlock_confirm}? Confirm or Cancel'
                elif not (self.unlock_transaction and self.unlock_transaction.busy):
                    self.unlock_transaction=UnlockTransaction(self.ownership,self.submit_read,desired=desired)
                    if getattr(self.scope._session._transport,'picto_batch_protocol',0)==1:
                        from expedition33.picto_batch import FrameBulkTransaction
                        self.unlock_bulk=FrameBulkTransaction(self.unlock_transaction)
                    else:self.unlock_bulk=BulkUnlockTransaction(self.unlock_transaction)
                    self.unlock_reported=None
                    self.unlock_bulk.start();self.unlock_confirm=None
                    self.bulk_message='Adding missing Pictos…' if desired else 'Removing; equipped protected'
            elif index==6:
                self.unlock_confirm=None
                if self.unlock_bulk is not None:self.unlock_bulk.stop()
                self.bulk_message='Cancelled remaining operations'
            elif index in (7,8,11):
                from expedition33.picto_bulk import PictoBulkJob
                if self.refresh_future is not None:
                    pending=self.refresh_future;self.refresh_future=None
                    try:pending.result()
                    except Exception:
                        # This is an unrelated read-only selection observation.
                        # Progression below performs its own fresh preflight.
                        log.warning('Discarded stale selection before bulk progression',exc_info=True)
                with self.operation():
                    # Refresh the actual inventory, never the menu's filtered list.
                    fresh=self.progression_catalog()
                    capability='picto_level_batch_protocol' if index==7 else 'picto_mastery_batch_protocol'
                    if getattr(self.scope._session._transport,capability,0)==1:
                        from expedition33.picto_inventory import PictoOwnership
                        from expedition33.picto_transactions import UnlockTransaction
                        from expedition33.picto_batch import FrameBulkTransaction
                        self.ownership=PictoOwnership(self.scope)
                        self.unlock_transaction=UnlockTransaction(self.ownership,self.submit_read)
                        if index==7:
                            system=self.one(o for o in fresh.select('BP_ItemUpgradeSystem_C') if not o.object_flags&0x30)
                            cls=fresh.find_class('BP_ItemInstance_Gear_C')
                            fn=self.one(o for o in fresh.objects if o.outer_index==cls.index and o.name=='ChangeLevel')
                            self.unlock_bulk=FrameBulkTransaction(self.unlock_transaction,level=(self.bulk_level,system,fn))
                        else:
                            characters=[o for o in fresh.select('BP_CharacterData_C') if not o.object_flags&0x30]
                            if not characters:raise RuntimeError('No live character for bulk mastery')
                            cls=fresh.find_class('BP_CharacterData_C')
                            fn=self.one(o for o in fresh.objects if o.outer_index==cls.index and o.name=='SetPassiveEffectSharedProgression')
                            table=self.one(o for o in fresh.objects if o.class_name=='DataTable' and fresh.path_name(o)=='/Game/Gameplay/Lumina/DT_PassiveEffects.DT_PassiveEffects')
                            self.unlock_bulk=FrameBulkTransaction(self.unlock_transaction,mastery=(index==8,characters[0],fn,table))
                        self.unlock_bulk.start()
                    else:self.bulk_job=PictoBulkJob(self.scope,fresh,'level' if index==7 else 'mastery',self.bulk_level if index==7 else index==8,self.preferences)
                self.bulk_message='Applying owned Pictos…'
            self.paint_value()
            return
        if self.bulk_job is not None:
            return
        if index==11 and not self.catalog_page:
            self.open_catalog('normal',self.definition_id);return
        if self.selection is None:return
        if self.catalog_page and index==11:
            self.catalog_action_error=(None,None)
            if self.definition_id in self.ownership_drafts:self.ownership_drafts.pop(self.definition_id)
            else:self.ownership_drafts[self.definition_id]=(True,False)
            self.paint_value();return
        if self.catalog_page and index==6 and self.definition_id in self.ownership_drafts:
            identity=self.definition_id
            # Removal is a separate explicit management action; retain all
            # ordinary property drafts and saved overrides for this identity.
            remembered=[('level',self.level,None)]+[('stat',v,k) for k,v in self.multipliers.items() if k in (1,6,8,9)]
            self.ownership.set_owned(identity,False,expected=True)
            self.preferences.remember_many(identity,remembered+[('owned',False,None)])
            self.ownership_drafts.pop(identity,None)
            if self.character is not None:self.ownership.refresh_panel(self.panel,self.character)
            self.ownership_ui_refresh();self.paint_value();return
        draft = self.draft()
        current = self.current_fields()
        if index != 6:
            if index < 4:
                self.mode='stat'; self.stat_key=tuple(self.stat_rows)[index]
            elif index in (7,8):
                if not self.progression_available or (index==8 and 'source' not in self.extra):return
                self.mode='level' if index==7 else 'mastery'
            elif index == 9:
                if not self.cost_available or 'source' not in self.extra:return
                self.mode='cost'
            elif index in (4,5):
                if self.mode in ('mastery','cost') and 'source' not in self.extra:return
                field_key = (self.mode, self.stat_key if self.mode == 'stat' else None)
                value = draft.value(field_key, current[field_key])
                if value is None:return
                if self.mode == 'stat':
                    value = round(max(0., min(10., value + (-.1 if index==4 else .1))), 3)
                elif self.mode == 'level':
                    value = max(1, min(33, value + (-1 if index==4 else 1)))
                elif self.mode == 'cost':
                    value = max(0, min(100, value + (-1 if index==4 else 1)))
                else:
                    value = index == 5
                draft.stage(field_key, value, current[field_key])
            self.paint_value()
            self.timings['draft_ms']=round((time.perf_counter()-started)*1000,1)
            return
        if not draft.changes:return
        previous,character = self.selection,self.character
        self.refresh_current()
        if not same_object(self.selection,previous) or not same_object(self.character,character):
            self.text(self.status_label,'Selection changed; draft retained');return
        if draft.conflicts(self.current_fields()):
            self.text(self.status_label,'Live values changed; review draft');return
        if 'source' not in self.extra and any(mode in ('mastery','cost') for mode,key in draft.changes):
            self.text(self.status_label,'Passive instance unavailable; draft retained');return
        # One Apply commits all fields. Level precedes explicit multipliers;
        # equipment and menu refresh happen only once after the complete edit.
        changes = sorted(draft.changes.items(), key=lambda entry: {'level':0,'stat':1,'mastery':2,'cost':3}[entry[0][0]])
        confirmed = []
        cost_changed = False
        with self.operation():
            try:
                from expedition33.picto_progression import change
                for (mode,key),value in changes:
                    baseline = draft.baselines[(mode,key)]
                    if mode == 'level':
                        change(self.scope,1,previous,self.fn('BP_ItemInstance_Gear_C','ChangeLevel'),None,self.panel,None,baseline,value)
                    elif mode == 'stat':
                        self.call(previous,'BP_ItemInstance_Gear_C','SetBaseStatsMultiplier',Stat=key,Value=value)
                        _,actual = self.read_stats(previous)
                        if abs(actual[key]-value)>1e-9:raise RuntimeError('Stat readback mismatch')
                    elif mode == 'cost':
                        change(self.scope,3,self.passive_table,self.fn('BP_CharacterData_C','RefreshUsedLuminaPointsInternal'),
                            self.extra['source'],self.panel,character,baseline,value)
                        cost_changed = True
                    else:
                        change(self.scope,2,character,self.fn('BP_CharacterData_C','SetPassiveEffectSharedProgression'),
                            self.extra['source'],self.panel,self.game_instance,self.extra['steps'],self.extra['threshold'] if value else 0)
                    confirmed.append((mode,value,key))
                    draft.acknowledge((mode,key))
                if any(mode in ('stat','level') for mode,_,_ in confirmed):
                    self.call(previous,'BP_ItemInstance_Gear_C','RefreshCurrentGearStats')
                    actual,multipliers=self.read_stats(previous)
                    for key in self.stat_rows:
                        if multipliers.get(key)==0 and actual.get(key,0)!=0:
                            change(self.scope,9,previous,self.fn('BP_ItemInstance_Gear_C','SetCurrentStatValue'),
                                None,None,None,int(actual[key]),key)
                    actual,multipliers=self.read_stats(previous)
                    level=next((value for mode,value,key in confirmed if mode=='level'),self.level)
                    expected=preview_stats(self.scaling,level,multipliers)
                    if any(actual.get(key,0)!=value for key,value in expected.items()):
                        raise RuntimeError('Applied stats do not match draft preview')
                self.call(character,'BP_CharacterData_C','UpdateEquipmentStats')
                for slot in range(3):self.call(self.panel,'WBP_Panel_Pictos_C','RefreshSlotData',InSlotIndex=slot)
            finally:
                # A later failure must not lose already acknowledged overrides.
                # The caller suspends after uncertain writes; never auto-retry.
                if confirmed:
                    self.preferences.remember_many(self.definition_id, confirmed)
        self.restore_queue = [entry for entry in self.restore_queue if entry[0] != self.definition_id]
        if cost_changed:
            try:self.refresh_lumina_ui()
            except RuntimeQueryError:self.lumina_ui_pending=True
        self.refresh_current()
        self.text(self.status_label,'All draft values applied and saved')
        self.timings['action_ms']=round((time.perf_counter()-started)*1000,1)
        log.info('Picto edit %s %d fields confirmed; timings=%s', self.definition_id, len(confirmed), self.timings)

    def poll(self):
        if self.state in ('failed', 'closed'):
            return
        try:
            with self.operation():
                self._poll()
        except BaseException as error:
            self.error = str(error)
            self.state = 'failed'
            log.exception('Picto reader stopped; no implicit restart')

    def _poll(self):
        if self.state in ('failed', 'closed'):
            return
        now = time.monotonic()
        try:
            if self.state == 'new':
                if now >= self.next_scan:
                    self.next_scan = now + .05
                    self.install()
                return
            if self.state == 'warm':
                if now >= self.next_scan:
                    self.next_scan = now + .03
                    self.attach_warm()
                return
            if self.catalog_future is not None and self.catalog_future.done():
                future,self.catalog_future=self.catalog_future,None
                try:
                    snapshot,self.catalog_metadata,self.catalog_ui_metadata,elapsed=future.result()
                    from expedition33.picto_inventory import PictoOwnership
                    self.ownership=PictoOwnership(self.scope,snapshot=snapshot)
                    self.timings['catalog_snapshot_ms']=round(elapsed*1000,2)
                except Exception as error:
                    self.catalog_request=None
                    self.text(self.status_label,'Catalog unavailable; retry from tools')
                    log.exception('Picto catalog snapshot failed; editor remains active')
            if self.ownership is not None:
                if self.native_catalog is None:
                    from expedition33.picto_catalog import NativeCatalog
                    self.native_catalog=NativeCatalog(self)
                    self.native_catalog.metadata=self.catalog_ui_metadata
                if not self.native_catalog.build_ready and self.native_catalog.build_error is None:
                    try:
                        if not hasattr(self,'catalog_build_started'):self.catalog_build_started=time.perf_counter()
                        step=time.perf_counter()
                        ready=self.native_catalog.build_step()
                        self.timings['catalog_build_max_step_ms']=max(self.timings.get('catalog_build_max_step_ms',0),round((time.perf_counter()-step)*1000,2))
                        if ready:
                            self.timings['catalog_build_ms']=round((time.perf_counter()-self.catalog_build_started)*1000,2)
                            log.info('Picto catalog controls prepared: %s',{k:v for k,v in self.timings.items() if k.startswith('catalog_')})
                    except Exception:
                        self.catalog_request=None
                        self.text(self.status_label,'Catalog construction failed; editor remains available')
                        log.exception('Picto catalog construction failed')
                if self.catalog_request is not None and self.native_catalog.build_ready:self.show_catalog()
            try:self.poll_unlock()
            except Exception as error:
                self.bulk_message='Unlock refresh failed: '+str(error)
                self.text(self.status_label,self.bulk_message)
                log.exception('Picto transaction refresh failed; filters remain available')
            for i, observer in enumerate(self.observers):
                if observer.state != 'active':
                    raise RuntimeError('Editor click observer expired')
                for event in observer.read(poll=i == 0):
                    try:self.activate(i)
                    except Exception as error:
                        # An uncertain write is never retried. Keep read-only
                        # browsing and filters alive, with a visible error.
                        self.bulk_message='Failed: '+str(error)
                        if self.catalog_page:
                            self.catalog_action_error=(self.catalog_selection,str(error))
                            try:self.paint_catalog()
                            except Exception:log.exception('Picto failure display deferred')
                        self.text(self.status_label,self.bulk_message)
                        log.exception('Picto action failed; catalog remains active')
            if self.catalog_page and self.native_catalog is not None:
                self.native_catalog.poll()
            if now >= self._renew_at:
                self.observers[0].renew()
                self._renew_at = now + 120
            if self.bulk_job is not None:
                job=self.bulk_job
                try:
                    job.tick()
                except Exception:
                    self.bulk_message=f'Stopped: {job.completed}/{job.total} applied'
                    self.paint_value()
                    raise
                if job.confirmed:
                    identity=job.confirmed.pop()
                    draft=self.drafts.get(identity)
                    if draft is not None:draft.acknowledge((job.mode,None))
                    saved_mode='mastered' if job.mode=='mastery' else 'owned' if job.mode=='unlock' else job.mode
                    self.restore_queue=[entry for entry in self.restore_queue if entry[:2]!=(identity,saved_mode)]
                if job.done:
                    self.bulk_message=f'{job.completed} Pictos updated and saved'
                    self.bulk_job=None
                    if job.mode=='unlock':
                        self.ownership_ui_refresh()
                    elif self.panel is not None:
                        from expedition33.picto_progression import change
                        character=self.reference(self.panel,'WBP_Panel_Pictos_C','CurrentCharacterData')
                        if character is not None:change(self.scope,11,self.panel,job.fn('WBP_Panel_Pictos_C','LoadCharacter'),character,None,None,0,0)
                    self.refresh_current()
                self.paint_value()
                return
            if self.lumina_ui_pending and self.selection is not None:
                try:self.refresh_lumina_ui()
                except RuntimeQueryError:pass
                else:self.lumina_ui_pending=False
            if self.refresh_future is not None and self.refresh_future.done():
                future=self.refresh_future
                self.refresh_future = None
                try:
                    result=future.result()
                except (RuntimeQueryError,RuntimeError) as error:
                    # Only a read failed: discard recycled identities and rediscover.
                    # Mutation exceptions take the separate fail-closed path below.
                    if getattr(self, '_observation_error', None) != str(error):
                        log.warning('Picto observation deferred: %s', error)
                    self._observation_error = str(error)
                    self.passives={}
                    self.next_scan=now+.1
                else:
                    self._observation_error = None
                    self.accept_observation(result)
            if self.restore_queue and not self.restore_error and self.refresh_future is None and self.character is not None:
                self.restore_one()
            if self.refresh_future is None and now >= self.next_scan and not (self.unlock_transaction and self.unlock_transaction.busy):
                self.next_scan = now + .03
                self.refresh_future = self.refresh_worker.submit(self.observe,
                    self.planner._catalog, self.view_catalog, self.catalog_selection if self.catalog_page else False)
        except BaseException as error:
            self.error = str(error)
            self.state = 'failed'
            trace = error.__traceback__
            while trace is not None:
                if trace.tb_frame.f_code.co_name == 'resolve':
                    log.error('Picto rejected observation: previous=%r incoming=%r',
                        trace.tb_frame.f_locals.get('current'), trace.tb_frame.f_locals.get('observed'))
                trace = trace.tb_next
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

    def restore_originals(self):
        """Undo configured overrides while retaining them for the next enable."""
        from expedition33.picto_restore import restore
        targets=self.baselines.targets(self.pid,tuple(self.preferences.profiles)) if self.preferences.profiles else {}
        # A saved bulk level/ownership choice is not a stat or cost override.
        # Restore those fields only if configured, or when recreating an item.
        for identity, baseline in tuple(targets.items()):
            configured=self.preferences.profiles[identity]
            if 'owned' in configured and configured['owned']!=baseline['owned']:
                continue
            keys=set(configured)
            if 'multipliers' in keys:keys.update(('stat_keys','multiplier_keys'))
            if 'mastered' in keys:keys.add('mastery_steps')
            targets[identity]={key:value for key,value in baseline.items() if key in keys}
        with self.operation():
            result=restore(self.scope,targets,catalog=self.progression_catalog()) if targets else {'missing':[],'applied':[]}
            if result['missing']:raise RuntimeError('Disable restoration incomplete: '+', '.join(result['missing']))
            # Disable can run from Pause after the stock Pictos panel closes.
            # Restoration refreshes gameplay data independently of that panel;
            # LoadCharacter requires an active panel and must not be dispatched
            # during teardown. The stock menu refreshes on its next activation.
        self.restore_queue.clear()
        log.info('Picto disable restoration: %s',result)
        return result

    def close(self, *, restore_originals=False):
        if self.unlock_bulk is not None:self.unlock_bulk.stop()
        if self.unlock_bulk is not None and getattr(self.unlock_bulk,'native',False) is True:
            job=self.unlock_bulk
            try:
                if job.future is not None:job.future.result(timeout=20.)
                job.poll()
                if job.done:
                    if getattr(job,'level',None):self.preferences.remember_field(job.completed+job.skipped,'level',job.level[0])
                    elif getattr(job,'mastery',None) is not None:self.preferences.remember_field(job.completed+job.skipped,'mastered',job.mastery[0])
                    else:self.preferences.remember_ownership(job.completed+job.skipped,job.transaction.desired)
            except Exception:log.exception('Bulk shutdown reconciliation incomplete; no mutation retry')
            self.unlock_bulk=None
        tx=self.unlock_transaction
        if tx is not None:
            if not tx.dispatched:
                if tx.future is not None:tx.future.cancel()
            else:
                try:
                    if tx.state in ('Unlocked','Already Owned','Removed','Already Absent'):
                        owned=tx.owned
                    else:
                        # Only reconcile an already-dispatched operation. Never
                        # poll preflight or invoke another mutation on shutdown.
                        future=tx.future or self.submit_read(tx._refresh)
                        owned=future.result(timeout=20.)
                    if (tx.identity in owned)==tx.desired:self.preferences.remember(tx.identity,'owned',tx.desired)
                    else:log.warning('Shutdown inventory did not confirm ownership change: %s',tx.identity)
                except Exception:log.exception('Ownership outcome unresolved during shutdown; no mutation retry')
        if self.native_catalog is not None:
            with self.operation():self.native_catalog.close()
        if self.refresh_future is not None:
            try:
                self.refresh_future.result()
            except Exception:
                log.exception('Picto observation failed during cleanup')
            self.refresh_future = None
        if self.bulk_job is not None and not self.bulk_job.done:
            # Finish post-edit equipment refresh after cancelling remaining work.
            with self.operation():
                self.bulk_job.queue.clear()
                self.bulk_job.tick()
            self.bulk_job=None
        restoration_error=None
        if restore_originals:
            try:self.restore_originals()
            except Exception as error:
                restoration_error=error
                log.exception('Picto disable restoration incomplete; saved configuration retained')
        with self.operation():self.card_layout.close()
        self.refresh_worker.submit(lambda: self.worker_reader.close() if self.worker_reader is not None else None).result()
        self.main_reader.close()
        self.refresh_worker.shutdown(wait=True, cancel_futures=True)
        for observer in self.observers:
            observer.close()
        self.observers.clear()
        if self.attachment is not None and not self.attachment.close():
            raise RuntimeError('Editor detach deferred; retain owner')
        if self.scope is not None:
            self.scope.close()
        self.state = 'closed'
        if restoration_error is not None:raise RuntimeError('Picto disable restoration incomplete; see diagnostics') from restoration_error


class Mod:
    def management(self):
        return ModDefinition('sdk.picto-editor', 'Picto Editor', version='0.7.0',
            description='Live controls attached to the stock Pictos menu.')

    def enable(self, session):
        self.session = session
        started = time.perf_counter()
        self.editor = StockEditor(session)
        try:
            from expedition33.picto_restore import restore
            with self.editor.operation():
                # Gameplay restoration needs no UMG discovery. Defer that scan
                # until install(), after the saved values are back in effect.
                startup_catalog = self.editor.progression_catalog()
                baseline=self.editor.baselines.capture(session,startup_catalog)
                log.info('Picto pre-override baseline: pid=%s definitions=%s',session.pid,len(baseline))
                self.editor.timings['baseline_ms']=round((time.perf_counter()-started)*1000,1)
                self.startup_restore = restore(session, self.editor.preferences.profiles, catalog=startup_catalog)
            self.editor.restore_queue.clear()
            self.editor.timings['restore_ms'] = round((time.perf_counter() - started) * 1000, 1)
            log.info('Picto startup restoration: %s', self.startup_restore)
        except Exception as error:
            self.editor.restore_error = str(error)
            log.exception('Picto startup restoration stopped; no mutation retry')
        self.editor.prepare_catalog()
        self.editor.poll()
        self.editor.timings['enable_ms'] = round((time.perf_counter() - started) * 1000, 1)
        log.info('Picto enable timings: %s', self.editor.timings)
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
        started=time.perf_counter()
        previous=getattr(self,'_poll_finished',started)
        try:self.editor.poll()
        finally:
            self._poll_finished=time.perf_counter()
            samples=getattr(self,'_poll_samples',[])
            samples.append(((started-previous)*1000,(self._poll_finished-started)*1000))
            self._poll_samples=samples
            if len(samples)>=30:
                log.info('Picto poll latency: outside_mean_ms=%.1f owner_mean_ms=%.1f owner_max_ms=%.1f',
                    sum(x[0] for x in samples)/len(samples),sum(x[1] for x in samples)/len(samples),max(x[1] for x in samples))
                self._poll_samples=[]

    def disable(self):
        self.editor.close(restore_originals=True)

