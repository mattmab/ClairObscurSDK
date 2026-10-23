"""Owned native Mods entry in this build's WBP_PauseMenu grid.

Uses the game's button Blueprint and observed text style. Native detach is
armed before borrowing the grid; click observation never changes engine calls.
"""
import logging
import time
from weakref import WeakSet
from dataclasses import replace
from contextlib import contextmanager
from .catalog import capture_matching, capture_selected
from .values import read_values, read_values_many, read_object_reference,read_values_with_references,StoredArray
from . import _ui_batch
from .invocation import prepare_call
from ._scope import SessionScope
from ._reader import ReadBatch, active_reader
from ._pause_attachment import PauseAttachment
from ._pause_clicks import PauseClicks
from . import RuntimeQueryError

log = logging.getLogger(__name__)

class PauseMenuEntry:
    _entries = WeakSet()

    def __init__(self, scope, service, *, label='Mods', readiness=None):
        if readiness is not None and not callable(readiness):
            raise TypeError('readiness must be a callable or None')
        if type(label) is not str or not label or len(label) > 32:
            raise ValueError('Pause entry label must contain 1 to 32 characters')
        self._readiness = readiness
        self._waiting_ready = False
        self.label = label
        self.parent_scope, self.service = scope, service
        self.scope = self.planner = self.observer = None
        self.attachment = None
        self.state = 'new'
        self.error = None
        self._next_scan = self._next_poll = self._renew_at = 0.
        self._renew_count = 900
        self._return_focus = False
        self._functions = {}
        self._next_world_check = 0.
        self._world_reader = None
        self._layout_calls = []
        self.timings = {}
        self._base_row = None
        self._entries.add(self)

    def _timed(self,name,callback,*args,**kwargs):
        started=time.perf_counter()
        try:return callback(*args,**kwargs)
        finally:
            row=self.timings.setdefault('operations',{}).setdefault(name,dict(count=0,total_ms=0.,max_ms=0.))
            elapsed=(time.perf_counter()-started)*1000
            row['count']+=1;row['total_ms']+=elapsed;row['max_ms']=max(row['max_ms'],elapsed)

    def _has_prepared_shell(self):
        # Routes share the parent's owned panel even when another view is bound.
        parent=getattr(self.service,'parent',self.service)
        menu=getattr(parent,'menu',None)
        return menu is not None and menu.panel.state=='built' and not getattr(parent,'_failure',None)

    def _choose_row(self, rows):
        # Keep the game's rows untouched. Share the original append boundary
        # among owners of this exact grid, including while one is rebuilding.
        bases = [entry._base_row for entry in self._entries
                 if entry is not self and entry.state in ('building', 'attached')
                 and entry.parent_scope.pid == self.parent_scope.pid
                 and getattr(entry, 'grid', None) == self.grid
                 and entry._base_row is not None]
        self._base_row = min(bases) if bases else max(rows) + 1
        reserved = {'Mods': 0, 'Map Travel': 1}
        if self.label in reserved:
            return self._base_row + reserved[self.label]
        return max(self._base_row + 2, max(rows) + 1)

    @staticmethod
    def current_entry(catalog):
        """Resolve the pause widget through its live local player controller.

        Old widgets can survive travel through our leases; enumeration alone
        cannot distinguish them from the current controller's pause widget.
        """
        candidates = []
        players=tuple(player for player in catalog.select('PlayerController') if not player.object_flags & 0x10)
        observed=read_values_many(catalog,players,fields=('Player','PauseMenuWidget'))
        for player in players:
            values = observed[player.index].values
            def field(name):
                found = [value for (_, key), value in values.items() if key == name]
                return found[0] if len(found) == 1 else None
            local_player = field('Player')
            pause = field('PauseMenuWidget')
            if (local_player is not None and local_player.class_name == 'LocalPlayer'
                    and pause is not None and pause.class_name == 'WBP_PauseMenu_C'):
                candidates.append((player, pause))
        if len(candidates) > 1:
            raise RuntimeError('Multiple local pause-menu owners; refusing ambiguous attachment')
        return candidates[0] if candidates else None

    @staticmethod
    def _same_bound_object(left,right):
        # GC flags are mutable observations. Identity, class and outer ownership
        # must still match after every fresh property/selected-object read.
        keys=('pid','index','serial','address','name','class_index','outer_index','outer_serial')
        return left is not None and right is not None and all(
            getattr(left,key)==getattr(right,key) for key in keys)

    def _same_binding(self,bound):
        return type(bound) is tuple and len(bound)==2 and all(self._same_bound_object(current,expected)
            for current,expected in zip(bound,(self.player,self.pause)))

    def _readiness_text(self):
        if self.label != 'Mods':
            return self.label
        progress = getattr(getattr(self.service, 'registry', None), '_startup_progress', None)
        if progress is None:
            return 'Mods [SDK starting]'
        completed, total = progress['completed'], progress['total']
        if progress['finished']:
            return ('Mods [SDK ready]' if not progress['failed']
                    else f"Mods [{progress['failed']} failed]")
        if progress.get('phase') == 'widgets':
            return 'Mods [SDK widgets...]'
        return f'Mods [SDK {completed}/{total}]'

    def grid_slots(self):
        """Read this grid's complete slot array without per-child engine calls."""
        values,catalog=read_values_with_references(self.planner._catalog,self.grid,fields=('Slots',))
        rows=[value for (_,name),value in values.values.items() if name=='Slots']
        if len(rows)!=1 or not isinstance(rows[0],StoredArray):
            raise RuntimeError('Pause grid slot array is unavailable')
        array=rows[0]
        if not 1<=array.length<=16 or len(array.items)!=array.length:
            raise RuntimeError('Pause grid slot array is incomplete or outside bounds')
        slots=tuple(array.items)
        if (any(slot is None or slot.class_name!='GridSlot' or slot.outer_index!=self.grid.index
                or slot.outer_serial!=self.grid.serial or slot.object_flags&0x30 for slot in slots)
                or len({(slot.index,slot.serial,slot.address) for slot in slots})!=len(slots)):
            raise RuntimeError('Pause grid slot ownership changed')
        self.planner.adopt_observations(catalog)
        return slots

    def _update_readiness(self):
        if self.label != 'Mods' or not hasattr(self, '_label_widget'):
            return
        text = self._readiness_text()
        if text == getattr(self, '_readiness_shown', None):
            return
        self._normal_label = self.prepare(self._label_widget,
            self.fn('TextBlock', 'SetText'), InText=text)
        self.invoke(self._normal_label)
        self._readiness_shown = text

    @property
    def available(self):
        t = getattr(self.parent_scope._session, '_transport', None)
        return (getattr(t, 'pause_attachment_protocol', 0) == 2 and
                getattr(t, 'trace_renew_protocol', 0) == 1)

    @staticmethod
    def one(items):
        rows = tuple(items)
        if len(rows) != 1: raise RuntimeError('Expected one verified pause-menu identity')
        return rows[0]

    def cls(self, name):
        c = self.planner._catalog
        return c.by_index[c.find_class(name).index]

    def fn(self, owner, name):
        key = (owner, name)
        if key not in self._functions:
            index = self.cls(owner).index
            self._functions[key] = self.one(o for o in self.planner._catalog.objects
                if o.outer_index == index and o.name == name)
        return self._functions[key]

    def stabilize_borrowed_targets(self,objects):
        from ._stable_lease import available,acquire_stable,fresh_catalog_replacing
        leases={}
        if not available(self.scope._session._transport):return leases
        for obj in objects:
            if obj.serial==0 and obj.index not in leases:
                lease,_=acquire_stable(self.scope,obj)
                leases[obj.index]=lease
        if leases:
            catalog=fresh_catalog_replacing(self.planner._catalog,
                tuple(lease.object for lease in leases.values()))
            self.planner.refresh_from(catalog)
        return leases

    def reference(self, obj, owner, name):
        owner_class=self.cls(owner)
        found, catalog = read_object_reference(self.planner._catalog, obj, owner_class, name, project=True)
        from ._stable_lease import available, stabilize_owned_tree, refresh_owned_tree_catalog
        owned_parent=available(self.scope._session._transport) and any(lease.active and lease._object is not None and
            (lease._object.index,lease._object.serial,lease._object.address)==(obj.index,obj.serial,obj.address)
            for lease in self.scope._leases)
        stable_field=((owner=='UserWidget' and name=='WidgetTree') or
                      (owner=='WBP_BaseButton_C' and name=='ButtonContent'))
        if (owned_parent and stable_field and found is not None and found.serial==0):
            field_args={} if name=='WidgetTree' else {'field':'ButtonContent'}
            stable_tree,_=stabilize_owned_tree(self.scope,catalog,obj,found,owner_class,**field_args)
            found,catalog=refresh_owned_tree_catalog(catalog,obj,found,stable_tree,owner_class.index,**field_args)
            self.planner.refresh_from(catalog)
        else:
            self.planner.adopt_observations(catalog)
        return found

    def layout(self, obj, owner, name, **args):
        if (not _ui_batch.layout_available(self.scope._session) or
                ((owner == 'GridSlot' or name in _ui_batch.EXTENDED_LAYOUT_SETTERS) and
                 not _ui_batch.extended_layout_available(self.scope._session))):
            return self.call(obj, owner, name, **args)
        self._layout_calls.append((obj, owner, name, args))

    def prepare(self,obj,function,**arguments):
        # Entry construction refreshes its planner while adopting owned child
        # trees. Keep only copied native schemas across those refreshes and
        # across title/pause entries; MetadataObservations resolves every
        # recorded dependency before reuse, and native dispatch checks again.
        cache=None
        if getattr(self,'_metadata_stable_ui',False) is True:
            from ._planning_metadata import MetadataObservations
            session=self.parent_scope._session
            cache=getattr(session,'_pause_schema_observations',None)
            if cache is None:
                cache=MetadataObservations();session._pause_schema_observations=cache
            self.planner._metadata._entries=dict(cache._entries)
        prepared=self.planner.prepare(obj,function,**arguments)
        if cache is not None:cache._entries=dict(self.planner._metadata._entries)
        return prepared

    def flush_layout(self):
        # Prepare only after creation/reference reads have revoked old plans.
        # Clear before dispatch: partial failure must never replay setters.
        calls, self._layout_calls = self._layout_calls, []
        for start in range(0, len(calls), _ui_batch.LIMIT):
            _ui_batch.invoke_setters(self.scope, [
                self.prepare(obj, self.fn(owner, name), **args)
                for obj, owner, name, args in calls[start:start + _ui_batch.LIMIT]])

    def call(self, obj, owner, name, **args):
        def run():
            with self.prepare(obj,self.fn(owner,name),**args).invoke(refresh_from_result=True) as result:
                return result.return_value
        return self._timed(owner+'.'+name,run)

    def create(self, obj, owner, name, **args):
        # Result remains scope-owned until complete entry teardown.
        def run():return self.prepare(obj,self.fn(owner,name),**args).invoke(refresh_from_result=True).return_value
        return self._timed(owner+'.'+name,run)

    def install(self):
        if self._readiness is not None and self._readiness() is not True:return False
        if self.state != 'new' or not self.available: return False
        started = time.perf_counter()
        from .pause_preparation import NAMES,capture as capture_prepared
        names=NAMES
        with ReadBatch(self.parent_scope.pid):
            # Capture descriptors and candidate owners only. Discover children
            # through this grid's verified getters, not all widget instances.
            def discover_metadata():
                return capture_matching(self.parent_scope.pid,names=names,
                    classes=('PlayerController','LocalPlayer','WBP_PauseMenu_C'))
            from ._metadata_stabilization import available,prepare_discovery
            catalog=capture_prepared(self.parent_scope._session,controller=getattr(self,'_expected_controller',None))
            if catalog is not None:
                self.metadata_uncovered_count=0;self._metadata_stable_ui=True
            elif available(getattr(self.parent_scope._session,'_transport',None)):
                catalog,uncovered=prepare_discovery(self.parent_scope._session,discover_metadata)
                self.metadata_uncovered_count=len(uncovered);self._metadata_stable_ui=True
            else:catalog=discover_metadata()
            self.timings['catalog_ms']=(time.perf_counter()-started)*1000
            if catalog.pid != self.parent_scope.pid:
                raise RuntimeError('Pause inventory belongs to another process')
            current = self.current_entry(catalog)
            if current is None: return False
            expected=getattr(self,'_expected_controller',None)
            if expected is not None:
                player=current[0]
                if (player.pid,player.index,player.serial,player.address)!=expected:return False
            self.timings['current_entry_ms']=(time.perf_counter()-started)*1000-self.timings['catalog_ms']
            self.player, self.pause = current
            self.scope = SessionScope(self.parent_scope)
            self.state = 'building'
            self.planner = self.scope.invocation_planner(selected_results=True,catalog=catalog)
            self.planner._require_stable_ui_identities=getattr(self,'_metadata_stable_ui',False)
            self.local_player = self.reference(self.player,'PlayerController','Player')
            local_values = read_values_many(self.planner._catalog, (self.local_player,),
                fields=('PlayerController',))[self.local_player.index]
            owner = self.one(k[0] for k in local_values.types if k[1] == 'PlayerController')
            self._local_player_owner = self.planner._catalog.by_index[owner]
            self.library = self.one(o for o in catalog.objects if o.name=='Default__WidgetBlueprintLibrary')
            gameplay = self.one(o for o in catalog.objects if o.name=='Default__GameplayStatics')
            resume = self.reference(self.pause,'WBP_PauseMenu_C','ResumeButton')
            resume_values = read_values_many(self.planner._catalog, (resume,),
                fields=('MinWidth', 'MinHeight'))[resume.index].values
            source_slot = self.reference(resume,'Widget','Slot')
            self.grid = self.reference(source_slot,'PanelSlot','Parent')
            if self.grid.class_name != 'GridPanel': raise RuntimeError('Pause button parent changed')
            pause_tree = self.reference(self.pause,'UserWidget','WidgetTree')
            source_text = self.one(o for o in catalog.select('CommonTextBlock')
                if o.outer_index == pause_tree.index and o.name == 'CommonTextBlock_178')
            style = self.reference(source_text,'CommonTextBlock','Style')
            if style is None: raise RuntimeError('Pause text style is unavailable')
            self.stabilize_borrowed_targets((self.pause,self.grid))
            self.pause=self.planner._catalog.by_index[self.pause.index]
            self.grid=self.planner._catalog.by_index[self.grid.index]
            bound=self.current_entry(self.planner._catalog)
            if not self._same_binding(bound):
                raise RuntimeError('Pause authority changed during target preparation')
            slots=self.grid_slots()
            if not any((slot.index,slot.serial,slot.address)==(source_slot.index,source_slot.serial,source_slot.address)
                    for slot in slots):raise RuntimeError('Resume slot is outside the current pause grid')
            slot_values = read_values_many(self.planner._catalog, slots, fields=('Row', 'Padding'))
            rows = [slot_values[o.index].values[self.cls('GridSlot').index,'Row'] for o in slots]
            self.row = self._choose_row(rows)
            if not 1 <= self.row <= 16: raise RuntimeError('Unexpected pause grid row count')
            padding = slot_values[source_slot.index].values[self.cls('GridSlot').index,'Padding']
            self.timings['discovery_ms'] = (time.perf_counter() - started) * 1000
            creation_started=time.perf_counter()
            self.button = self.create(self.library,'WidgetBlueprintLibrary','Create',
                WorldContextObject=self.player, WidgetType=self.cls('WBP_BaseButton_C'), OwningPlayer=self.player)
            self.attachment = PauseAttachment(self.scope) # Publish before arming native cleanup.
            lease = self.one(l for l in self.scope._leases if l.active and l.object == self.button)
            remove = prepare_call(self.planner._catalog,self.button,self.fn('Widget','RemoveFromParent'),{})
            self.attachment.arm(lease,remove)
            button_tree = self.reference(self.button,'UserWidget','WidgetTree')
            content = self.reference(self.button,'WBP_BaseButton_C','ButtonContent')
            label = self.create(gameplay,'GameplayStatics','SpawnObject',ObjectClass=self.cls('CommonTextBlock'),Outer=button_tree)
            self.layout(label,'CommonTextBlock','SetStyle',InStyle=style)
            self.layout(label,'TextBlock','SetText',InText=self.label)
            self.layout(label,'TextLayoutWidget','SetJustification',InJustification=1)
            frame = self.create(gameplay,'GameplayStatics','SpawnObject',ObjectClass=self.cls('Overlay'),Outer=button_tree)
            label_slot = self.create(frame,'Overlay','AddChildToOverlay',Content=label)
            self.layout(label_slot,'OverlaySlot','SetHorizontalAlignment',InHorizontalAlignment=2)
            self.layout(label_slot,'OverlaySlot','SetVerticalAlignment',InVerticalAlignment=2)
            self.call(content,'ContentWidget','SetContent',Content=frame)
            self.layout(self.button,'CommonButtonBase','SetMinDimensions',
                InMinWidth=resume_values[self.cls('CommonButtonBase').index,'MinWidth'],
                InMinHeight=resume_values[self.cls('CommonButtonBase').index,'MinHeight'])
            self.layout(self.button,'CommonButtonBase','SetIsSelectable',bInIsSelectable=False)
            self.layout(self.button,'CommonButtonBase','SetIsToggleable',bInIsToggleable=False)
            self.timings['button_contents_ms']=(time.perf_counter()-creation_started)*1000
            attachment_started=time.perf_counter()
            pause_panel = self.reference(self.pause,'WBP_PauseMenu_C','PausePanel')
            stable_panels=self.stabilize_borrowed_targets((pause_panel,))
            pause_panel=self.planner._catalog.by_index[pause_panel.index]
            bound=self.current_entry(self.planner._catalog)
            actual_panel=self.reference(self.pause,'WBP_PauseMenu_C','PausePanel')
            if not self._same_binding(bound) or not self._same_bound_object(actual_panel,pause_panel):
                raise RuntimeError('Pause restore panel authority changed during preparation')
            panel_lease = stable_panels.get(pause_panel.index)
            if panel_lease is None:panel_lease=self.scope.retain(pause_panel)
            original_opacity = self.call(pause_panel,'Widget','GetRenderOpacity')
            original_enabled = self.call(pause_panel,'Widget','GetIsEnabled')
            def simple(name, **args):
                return replace(self.prepare(pause_panel,self.fn('Widget',name),**args)._plan,wire_version=1)
            self.attachment.arm_restore(panel_lease,
                simple('SetRenderOpacity',InOpacity=original_opacity),
                simple('SetIsEnabled',bInIsEnabled=original_enabled))
            self._hide_opacity = simple('SetRenderOpacity',InOpacity=0.)
            self._hide_enabled = simple('SetIsEnabled',bInIsEnabled=False)
            self.observer = PauseClicks(self.scope._session,self.fn('CommonButtonBase','HandleButtonClicked'),
                self.button,self.planner._catalog)
            self._renew_at = time.monotonic() + 120
            self.flush_layout()
            slot = self.create(self.grid,'GridPanel','AddChildToGrid',Content=self.button,InRow=self.row,InColumn=0)
            self.layout(slot,'GridSlot','SetPadding',InPadding=dict(padding.fields))
            self.layout(slot,'GridSlot','SetHorizontalAlignment',InHorizontalAlignment=0)
            self.layout(slot,'GridSlot','SetVerticalAlignment',InVerticalAlignment=0)
            self.flush_layout()
            self.timings['attachment_ms']=(time.perf_counter()-attachment_started)*1000
            self._active_call = self.prepare(self.pause,self.fn('CommonActivatableWidget','IsActivated'))
            self._viewport_focus = self.prepare(self.library,self.fn('WidgetBlueprintLibrary','SetFocusToGameViewport'))
            self._button_focus = self.prepare(self.button,self.fn('Widget','SetUserFocus'),PlayerController=self.player)
            self._loading_label = self.prepare(label,self.fn('TextBlock','SetText'),InText='Constructing widgets...')
            self._cleanup_label = self.prepare(label,self.fn('TextBlock','SetText'),InText='Deconstructing widgets...')
            self._normal_label = self.prepare(label,self.fn('TextBlock','SetText'),InText=self.label)
            self._label_widget = label
            self.state = 'attached'
            self._update_readiness()
            self.timings['total_ms'] = (time.perf_counter() - started) * 1000
            log.info('Native Mods pause entry attached: pause=%s button=%s row=%d style=%s (attach %.3fs)',
                self.pause.index,self.button.index,self.row,style.name,time.perf_counter()-started)
        return True

    @staticmethod
    def invoke(prepared):
        with prepared.invoke() as result: return result.return_value

    def open(self):
        """Open through the same pause-conceal lifecycle as the native button."""
        if self.state != 'attached':
            raise RuntimeError('Pause entry must be attached before structured menu open')
        if self.invoke(self._active_call):
            self._open_from_pause()
        else:
            self.service.open()

    def _open_from_pause(self):
        if self.service.menu is None or self.service.menu.panel.state != 'open':
            opened_started=time.perf_counter()
            warm=self._has_prepared_shell()
            if not warm:self._timed('open_loading_label',self.invoke,self._loading_label)
            if not self._timed('open_conceal',self.attachment.show_busy,self._hide_enabled):
                raise RuntimeError('Pause conceal deferred; restore through cleanup')
            try:
                # Disabling the old panel can move focus. Establish the
                # required viewport baseline after that transition.
                self._timed('open_viewport',self.invoke,self._viewport_focus)
                self._timed('open_service',self.service.open)
                if not self._timed('open_hide',self.attachment.hide_busy,self._hide_opacity):
                    raise RuntimeError('Pause hide deferred')
            except BaseException:
                # Restore the borrowed pause UI even when SDK preparation
                # fails before an open menu exists. Do not retry opening.
                if not self.attachment.restore():
                    raise RuntimeError('Failed-open pause restoration deferred; retain owner')
                if self.invoke(self._active_call): self.invoke(self._button_focus)
                raise
            finally:
                if not warm:self._timed('open_normal_label',self.invoke,self._normal_label)
                self.timings['open_total_ms']=(time.perf_counter()-opened_started)*1000
                log.info('Pause entry open timing: %s',self.timings)
            self._return_focus = True
            log.info('Native Mods pause click opened SDK menu')

    @contextmanager
    def cleanup_feedback(self):
        visible = self.state == 'attached' and self.invoke(self._active_call)
        try:
            if visible:
                self.invoke(self._cleanup_label)
                if not self.attachment.show_busy(self._hide_enabled):
                    raise RuntimeError('Pause cleanup feedback deferred')
            yield
        finally:
            if visible:
                self.invoke(self._normal_label)
                if not self.attachment.restore():
                    raise RuntimeError('Pause cleanup restoration deferred')

    @contextmanager
    def _world_read_operation(self):
        """Reuse process validation, never controller or UObject observations."""
        if active_reader() is not None:
            with ReadBatch(self.parent_scope.pid):
                yield
            return
        if self._world_reader is None:
            self._world_reader = ReadBatch(self.parent_scope.pid, share=True)
        reader = self._world_reader
        try:
            with reader.bind():
                yield
        except BaseException:
            # No retry: poll retains its failed lifecycle state. A failed
            # read-only subprocess must not remain available to later work.
            try:
                reader.close()
            finally:
                self._world_reader = None
            raise

    def poll(self):
        if self._readiness is not None:
            readiness = self._readiness()
            if readiness is None:return
            if type(readiness) is not bool:raise TypeError('readiness must return bool or None')
            if readiness is False:
                # Never install at title; close old owners through normal cleanup.
                # A failed close keeps the owner and retries only its cleanup.
                if self.state not in ('new', 'closed'):
                    self.close()
                    self._waiting_ready = True
                return
            if self._waiting_ready:
                parent, service, label, readiness = self.parent_scope, self.service, self.label, self._readiness
                self.__init__(parent, service, label=label, readiness=readiness)
        if not self.available or self.state == 'closed': return
        if self.state == 'failed':
            if (self.error != 'RuntimeError: Pause click observer expired or stopped; no silent reinstallation'
                    or self.observer is None or self.observer.state not in ('expired', 'capped', 'active')):
                return
            try:
                self.observer.recover()
            except BaseException as error:
                self.error = f'{type(error).__name__}: {error}'
                log.exception('Pause observer recovery failed; owner retained')
                return
            self.state, self.error = 'attached', None
            log.info('Recovered expired pause click subscription')
        now = time.monotonic()
        try:
            if self.state == 'new':
                if now < self._next_scan: return
                self._next_scan = now + .25
                self.install()
                return
            if self.state != 'attached' or now < self._next_poll: return
            self._next_poll = now + .02
            if now >= self._next_world_check:
                # A reader is retained on this owner thread between checks;
                # each check still captures the live identity and property.
                self._next_world_check = now + .25
                with self._world_read_operation():
                    # Travel may reuse slots from the old world's catalog. Do
                    # not merge the replacement controller into that inventory.
                    # The persistent LocalPlayer and its fresh class closure are
                    # sufficient for this identity-checked, read-only observation.
                    fresh = capture_selected(self.parent_scope.pid, ((self.local_player.index,
                        self.local_player.serial, self.local_player.address),))
                    current, _ = read_object_reference(fresh, self.local_player,
                        self._local_player_owner, 'PlayerController')
                if current is not None and (current.index, current.serial, current.address) != (self.player.index, self.player.serial, self.player.address):
                    # Complete acknowledged cleanup before relinquishing ownership.
                    # Any failure below keeps this instance failed with its owners.
                    self.close()
                    self.service.dispose_menu()
                    self.service._warmup_attempted = False
                    parent, service = self.parent_scope, self.service
                    self.__init__(parent, service, label=self.label, readiness=self._readiness)
                    log.info('Pause owner changed after travel; old entry removed, rebuilding for current controller')
                    return
            self._update_readiness()
            events = self.observer.read()
            if self.observer.state != 'active':
                raise RuntimeError('Pause click observer expired or stopped; no silent reinstallation')
            if now >= self._renew_at or self.observer._observed >= self._renew_count:
                self.observer.renew()
                self._renew_at = now + 120
                self._renew_count = self.observer._observed + 900
            if events and self.invoke(self._active_call):
                self._open_from_pause()
            if self._return_focus and (self.service.menu is None or self.service.menu.panel.state in ('built','closed')):
                self._return_focus = False
                if not self.attachment.restore():
                    raise RuntimeError('Pause restoration deferred; retain its owner')
                if self.invoke(self._active_call): self.invoke(self._button_focus)
                log.info('SDK menu closed; focus returned to native Mods entry')
        except BaseException as error:
            # Discovery may race GC during startup or an SDK restart. Nothing
            # has been borrowed or mutated while state is still new. Discard
            # that observation and let the next bounded scan start afresh.
            if (self.state == 'new' and isinstance(error, RuntimeQueryError)
                    and any(reason in str(error) for reason in ('DESCRIPTOR_IDENTITY_CHANGED', 'MATCH_TYPE_NOT_REGISTERED'))):
                log.info('Pause discovery is not ready; waiting for the next bounded scan')
                return
            self.state, self.error = 'failed', f'{type(error).__name__}: {error}'
            log.exception('Pause entry suspended; owner retained for cleanup')

    def retire_world(self):
        if self.state == 'closed':return 'ack'
        self._return_focus=False
        if self._world_reader is not None:self._world_reader.close();self._world_reader=None
        if self.observer is not None:self.observer.close();self.observer=None
        if self.attachment is not None:
            if not self.attachment.retire_world():return 'pending'
        if self.scope is not None:self.scope.close()
        self.state='closed';return 'ack'

    def close(self):
        if self.state == 'closed': return
        self._return_focus = False
        if self._world_reader is not None:
            self._world_reader.close()
            self._world_reader = None
        if self.observer is not None:
            self.observer.close()
            self.observer = None
        if self.attachment is not None and not self.attachment.close():
            raise RuntimeError('Pause entry detach deferred; retain its owner')
        if self.scope is not None: self.scope.close()
        self.state = 'closed'
        log.info('Native Mods pause entry removed')
