"""Presentation-only catalog and bounded native scrolling row window.

No inventory objects are fabricated. Definitions remain plain Python records;
only the visible rows are represented by SDK-owned native buttons.
"""
import math
import time


class CatalogView:
    COLUMNS = 2
    ROW_HEIGHT = 132.0
    POOL_SIZE = 26
    PRELOAD_ROWS = 3
    ROW_TEXT_WIDTH = 270

    def __init__(self, definitions, owned, *, experimental=False):
        self.definitions, self.owned = definitions, owned
        self.experimental = experimental
        self.filter = 'all'
        self.query = ''
        self.ids = []
        self.rebuild()

    def rebuild(self):
        query = self.query.casefold().strip()
        self.ids = sorted((key for key, row in self.definitions.items()
            if row['normal'] != self.experimental
            and (self.filter == 'all' or (key in self.owned) == (self.filter == 'owned'))
            and (not query or query in row['name'].casefold() or query in key.casefold())),
            key=lambda key: (self.definitions[key]['name'].casefold(), key))

    @property
    def counts(self):
        gameplay = {key for key, row in self.definitions.items() if row['normal']}
        owned = len(gameplay.intersection(self.owned))
        return {'gameplay': len(gameplay), 'owned': owned,
                'locked': len(gameplay) - owned,
                'experimental': len(self.definitions) - len(gameplay)}

    @property
    def filter_label(self):
        return 'Experimental' if self.experimental else {
            'all': 'All Pictos', 'owned': 'Owned Only', 'locked': 'Locked Only'}[self.filter]

    def reconcile_selection(self, selected, previous_ids=()):
        if selected in self.ids:
            return selected
        if not self.ids:
            return None
        previous = list(previous_ids)
        index = previous.index(selected) if selected in previous else 0
        return self.ids[min(index, len(self.ids) - 1)]

    @property
    def height(self):
        return max(840., math.ceil(len(self.ids) / self.COLUMNS) * self.ROW_HEIGHT)

    def window(self, offset):
        if not math.isfinite(offset):
            raise ValueError('Invalid catalog scroll offset')
        row = max(0, int(offset // self.ROW_HEIGHT) - self.PRELOAD_ROWS)
        start = min(row * self.COLUMNS, max(0, len(self.ids) - self.POOL_SIZE))
        start -= start % self.COLUMNS
        return start, self.ids[start:start + self.POOL_SIZE]


def prepare_metadata(pid):
    """Capture catalog-only reflection on the caller's read worker.

    The returned schema snapshot is adopted by build(), which performs only
    already-resolved native widget operations on the UI owner thread.
    """
    from .catalog import capture_matching
    fresh = capture_matching(pid, names=('ScrollBox', 'ScrollBoxSlot',
        'SizeBox', 'PanelWidget', 'WBP_PictosList_C',
        'AddChild', 'GetScrollOffset', 'SetScrollOffset', 'ScrollToEnd', 'SetHeightOverride',
        'SetWidthOverride', 'GetVisibility', 'SetVisibility'))
    return fresh.subset(o for o in fresh.objects if o.index in fresh.classes or
        o.class_name in ('Function', 'Enum', 'UserDefinedEnum'))


class NativeCatalog:
    """Temporarily replace the stock left list with a native ScrollBox.

    Uses existing widget leases, reflected calls, batched layout and click
    observation. The stock list retains its items and callbacks while hidden.
    """
    def __init__(self, editor):
        self.e = editor
        self.root = None
        self.stock = None
        self.saved_visibility = None
        self.visible = False
        self.mapping = {}
        self.rendered = None
        self.row_state = {}
        self.actions = {}
        self.hidden_stock = []
        self.offsets = {}
        self.filter_key = None
        self.previous_ids = ()
        self.details = {}
        self.metadata = None
        self._details_rendered = None
        self.build_ready = False
        self.build_error = None
        self._build_iterator = None

    def begin_build(self):
        """Arm construction without invoking native work or hiding stock UI."""
        if self.build_error is not None:
            raise RuntimeError('Catalog build previously failed; rebuild the editor session') from self.build_error
        if not self.build_ready and self._build_iterator is None:
            if self.metadata is None:
                raise RuntimeError('Catalog metadata is not ready; prepare it on the reader worker')
            self._build_iterator = self._build_steps()
        return self.build_ready

    def build_step(self, max_ms=80):
        """Bound structural work by elapsed time, stopping after one button.

        Each native call is indivisible; the budget cannot interrupt one call or
        button construction. Called on the UI owner thread in its operation
        scope. Temporary canvas state is restored at every generator yield.
        """
        if not isinstance(max_ms, (int, float)) or not math.isfinite(max_ms) or max_ms <= 0:
            raise ValueError('Catalog build budget must be positive and finite')
        self.begin_build()
        if self.build_ready:
            return True
        started = time.perf_counter()
        try:
            while True:
                boundary = next(self._build_iterator)
                self.e.flush_layout()
                self.e.ui_planner.adopt_observations(self.e.planner._catalog)
                if boundary == 'button' or (time.perf_counter() - started) * 1000 >= max_ms:
                    break
        except StopIteration:
            self._build_iterator = None
            self.build_ready = True
        except Exception as error:
            self.build_error = error
            self._build_iterator.close()
            self._build_iterator = None
            raise
        return self.build_ready

    def build(self):
        """Blocking compatibility; production callers should use build_step."""
        while not self.build_step():
            pass

    def _on_canvas(self, canvas, function, *args):
        original = self.e.canvas
        try:
            self.e.canvas = canvas
            return function(*args)
        finally:
            self.e.canvas = original

    def _build_steps(self):
        e = self.e
        # Reflection is prepared by the reader worker before opening the UI.
        fresh = self.metadata
        if fresh is None:
            raise RuntimeError('Catalog metadata is not ready; prepare it on the reader worker')
        e.planner.adopt_observations(fresh)
        from .enums import describe_enums
        enum = e.planner._catalog.find_path('/Script/UMG.ESlateVisibility', 'Enum')
        descriptor = describe_enums(e.planner._catalog, (enum,))[enum.index]
        self.hidden_value = descriptor.value('ESlateVisibility::Hidden')
        self.visible_value = descriptor.value('ESlateVisibility::Visible')
        self.container_visibility = descriptor.value('ESlateVisibility::SelfHitTestInvisible')
        self.stock = e.reference(e.panel, 'WBP_Panel_Pictos_C', 'PictosList')
        if self.stock is None or self.stock.class_name != 'WBP_PictosList_C':
            raise RuntimeError('Native Picto list identity unavailable')
        self.root = e.spawn('SizeBox')
        yield
        self.frame = e.spawn('CanvasPanel')
        yield
        e.call(self.frame, 'Widget', 'SetVisibility', InVisibility=self.container_visibility)
        yield
        self.scroll = e.spawn('ScrollBox')
        yield
        self.extent = e.spawn('SizeBox')
        yield
        self.canvas = e.spawn('CanvasPanel')
        yield
        e.call(self.root, 'Widget', 'SetVisibility', InVisibility=self.hidden_value)
        yield
        e.call(self.root, 'SizeBox', 'SetWidthOverride', InWidthOverride=1530.)
        yield
        e.call(self.root, 'SizeBox', 'SetHeightOverride', InHeightOverride=1065.)
        yield
        e.call(self.root, 'ContentWidget', 'SetContent', Content=self.frame)
        yield
        e.place(self.frame, self.scroll, 0, 225, 690, 840)
        yield
        e.create(self.scroll, 'PanelWidget', 'AddChild', Content=self.extent)
        yield
        e.call(self.extent, 'ContentWidget', 'SetContent', Content=self.canvas)
        yield
        e.call(self.extent, 'SizeBox', 'SetWidthOverride', InWidthOverride=670.)
        yield
        e.call(self.extent, 'SizeBox', 'SetHeightOverride', InHeightOverride=840.)
        yield
        library = e.one(o for o in e.planner._catalog.objects if o.name == 'Default__WidgetBlueprintLibrary')
        self.rows = []
        self.title_label = self._on_canvas(self.frame, e.make_label, 'PICTO CATALOG', 0, 0, 690, 42)
        yield
        self.count_label = self._on_canvas(self.frame, e.make_label, '', 0, 44, 690, 40)
        yield
        self.filter_label = self._on_canvas(self.frame, e.make_label, '', 0, 172, 690, 40)
        yield
        for index, (action, title) in enumerate((('all', 'All Pictos'),
                ('owned', 'Owned Only'), ('locked', 'Locked Only'),
                ('experimental', 'Experimental'))):
            self.actions[len(e.buttons)] = 'filter:' + action
            self._on_canvas(self.frame, e.make_button, library, title, index * 171, 92, 165, 72)
            yield 'button'
        self.details_label = self._on_canvas(self.frame, e.make_label, '', 920, 315, 600, 490)
        yield
        e.call(self.details_label, 'TextBlock', 'SetAutoWrapText', InAutoTextWrap=True)
        yield
        e.call(self.details_label, 'CommonTextBlock', 'SetWrapTextWidth', InWrapTextAt=580)
        yield
        self.actions[len(e.buttons)] = 'unlock'
        self.unlock_button, self.unlock_label = self._on_canvas(self.frame, e.make_button, library, 'Unlock Picto', 920, 830, 365, 55)
        yield 'button'
        self.actions[len(e.buttons)] = 'tools'
        self._on_canvas(self.frame, e.make_button, library, 'Tools', 1295, 830, 225, 55)
        yield 'button'
        self.first_button = len(e.buttons)
        for index in range(CatalogView.POOL_SIZE):
            button, label = self._on_canvas(self.canvas, e.make_button, library, '', 0, 0, 320, 126)
            # The native button's slanted frame needs a wider horizontal inset
            # than rectangular controls. Keep full names, wrapping before it.
            e.call(label, 'CommonTextBlock', 'SetWrapTextWidth', InWrapTextAt=CatalogView.ROW_TEXT_WIDTH)
            slot = e.button_slots[button.index]
            self.rows.append((button, label, slot))
            yield 'button'
        e.flush_layout()
        yield
        slot = e.create(e.host, 'GridPanel', 'AddChildToGrid', Content=self.root, InRow=0, InColumn=0)
        yield
        e.call(slot, 'GridSlot', 'SetPadding', InPadding={'Left':35., 'Top':80., 'Right':0., 'Bottom':0.})
        yield
        e.call(slot, 'GridSlot', 'SetHorizontalAlignment', InHorizontalAlignment=1)
        yield
        e.call(slot, 'GridSlot', 'SetVerticalAlignment', InVerticalAlignment=1)
        yield
        e.call(slot, 'GridSlot', 'SetLayer', InLayer=101)
        yield
        e.call(self.root, 'Widget', 'SetRenderTransformPivot', Pivot={'X':0., 'Y':0.})
        yield
        e.call(self.root, 'Widget', 'SetRenderScale', Scale={'X':.8, 'Y':.8})
        yield
        e.ui_planner.adopt_observations(e.planner._catalog)
        yield

    def show(self, view):
        if not self.build_ready:
            raise RuntimeError('Catalog is still preparing; continue build_step before show')
        self.view = view
        e = self.e
        if not self.visible:
            self.saved_visibility = e.call(self.stock, 'Widget', 'GetVisibility')
            # Record the restore obligation before either visibility mutation.
            self.visible = True
            e.call(self.stock, 'Widget', 'SetVisibility', InVisibility=self.hidden_value)
            for name in ('WBP_PictoSlot0', 'WBP_PictoSlot1', 'WBP_PictoSlot2'):
                widget = e.reference(e.panel, 'WBP_Panel_Pictos_C', name)
                if widget is not None:
                    visibility = e.call(widget, 'Widget', 'GetVisibility')
                    self.hidden_stock.append((widget, visibility))
                    e.call(widget, 'Widget', 'SetVisibility', InVisibility=self.hidden_value)
            e.call(self.root, 'Widget', 'SetVisibility', InVisibility=self.container_visibility)
        self.reset()

    def reset(self, preserve_scroll=True):
        e = self.e
        old_key = self.filter_key
        key = (self.view.experimental, self.view.filter, self.view.query)
        offset = e.call(self.scroll, 'ScrollBox', 'GetScrollOffset') if self.visible else 0.
        # Fake editors and a not-yet-mounted widget may not return a number.
        if not isinstance(offset, (int, float)) or not math.isfinite(offset):
            offset = 0.
        if old_key is not None:
            self.offsets[old_key] = offset
        self.view.rebuild()
        old_selection = e.catalog_selection
        e.catalog_selection = self.view.reconcile_selection(old_selection, self.previous_ids)
        self.previous_ids = tuple(self.view.ids)
        self.filter_key = key
        e.call(self.extent, 'SizeBox', 'SetHeightOverride', InHeightOverride=self.view.height)
        desired = self.offsets.get(key, 0.) if key != old_key else offset
        if not preserve_scroll:
            desired = 0.
        desired = min(max(0., desired), max(0., self.view.height - 840.))
        if e.catalog_selection is not None and e.catalog_selection != old_selection:
            # A filtered-out selection falls back near its old index. Keep the
            # replacement visible without disturbing retained selections.
            selected_row = self.view.ids.index(e.catalog_selection) // self.view.COLUMNS
            top = selected_row * self.view.ROW_HEIGHT
            bottom = top + self.view.ROW_HEIGHT
            if top < desired:
                desired = float(top)
            elif bottom > desired + 840.:
                desired = float(bottom - 840.)
            desired = min(max(0., desired), max(0., self.view.height - 840.))
        if desired != offset:
            e.call(self.scroll, 'ScrollBox', 'SetScrollOffset', NewScrollOffset=desired)
        self.rendered = None
        self.paint_header()
        self.poll()

    def paint_header(self):
        if not hasattr(self, 'title_label'):
            return
        counts = self.view.counts
        self.e.text(self.count_label, f"{counts['gameplay']} gameplay | {counts['owned']} owned | {counts['locked']} locked")
        self.e.text(self.filter_label, f"{self.view.filter_label} | {len(self.view.ids)} Pictos | A–Z")

    def update_details(self, snapshot):
        """Present verified values supplied by the editor's reader worker.

        Required identity/owned/normal refer to the selected catalog record.
        Optional level/mastery/cost/health/defense/speed/critical_rate/effect/
        acquisition are already formatted values; missing data stays unavailable.
        ``state`` is a transaction status, and ``message`` is its explanation.
        No reads or mutations are initiated by this presentation method.
        """
        self.details = dict(snapshot)
        if not self.build_ready or not hasattr(self, 'details_label'):
            return
        if self.details == self._details_rendered:
            return
        e = self.e
        e.text(self.details_label, details_text(snapshot))
        owned = bool(snapshot.get('owned'))
        pending = snapshot.get('state') == 'Unlocking'
        e.text(self.unlock_label, 'Owned' if owned else 'Unlocking…' if pending else 'Unlock Picto')
        e.defer_layout(self.unlock_button, 'Widget', 'SetIsEnabled',
                       bInIsEnabled=bool(snapshot.get('identity') and snapshot.get('normal') and not owned and not pending))
        e.flush_layout()
        self.paint_header()
        # Commit only after native setters complete; a failed render can retry.
        self._details_rendered = dict(self.details)

    def poll(self):
        if not self.visible:
            return
        e = self.e
        offset = e.call(self.scroll, 'ScrollBox', 'GetScrollOffset')
        start, ids = self.view.window(offset)
        state = (start, tuple(ids), e.catalog_selection, frozenset(self.view.owned))
        if state == self.rendered:
            return
        # Do not reinterpret a queued click using a different pool mapping:
        # editor drains click observations before calling this method.
        mapping = {}
        row_state = {}
        texts = {}
        # Circular slots keep overlapping definitions on the same button. A
        # one-row scroll changes two off-screen buttons, not the entire pool.
        assignments = {(start + i) % len(self.rows): (start + i, identity)
                       for i, identity in enumerate(ids)}
        for index, (button, label, slot) in enumerate(self.rows):
            absolute, identity = assignments.get(index, (None, None))
            previous = self.row_state.get(index)
            if previous is None or bool(previous[0]) != bool(identity):
                e.defer_layout(button, 'Widget', 'SetVisibility', InVisibility=self.visible_value if identity else self.hidden_value)
            if identity is None:
                row_state[index] = (None, None, None)
                continue
            if previous is None or previous[2] != absolute:
                e.defer_layout(slot, 'CanvasPanelSlot', 'SetPosition', InPosition={
                    'X':float(absolute % 2 * 335), 'Y':float(absolute // 2 * self.view.ROW_HEIGHT)})
            name = self.view.definitions[identity]['name']
            title = name
            title = ('> ' if identity == e.catalog_selection else '') + title + ('\nOwned' if identity in self.view.owned else '\nLocked')
            if previous is None or previous[1] != title:
                e.defer_layout(label, 'TextBlock', 'SetText', InText=title)
                texts[label.index] = title
            row_state[index] = (identity, title, absolute)
            mapping[self.first_button + index] = identity
        e.flush_layout()
        e._text.update(texts)
        self.row_state = row_state
        # Discard row clicks that arrived while pooled rows were being rebound.
        # They must never be delivered against a different definition.
        for index, observer in enumerate(e.observers[self.first_button:self.first_button + len(self.rows)]):
            observer.read(poll=index == 0)
        self.mapping = mapping
        self.rendered = state

    def hide(self):
        if self.visible:
            self.e.call(self.root, 'Widget', 'SetVisibility', InVisibility=self.hidden_value)
            self.e.call(self.stock, 'Widget', 'SetVisibility', InVisibility=self.saved_visibility)
            for widget, visibility in self.hidden_stock:
                self.e.call(widget, 'Widget', 'SetVisibility', InVisibility=visibility)
            self.hidden_stock.clear()
            self.visible = False
            self.mapping.clear()

    def close(self):
        if self._build_iterator is not None:
            self._build_iterator.close()
            self._build_iterator = None
        self.hide()
        if self.root is not None:
            self.e.call(self.root, 'Widget', 'RemoveFromParent')


def details_text(snapshot):
    """Format only confirmed metadata; locked definitions have no item level."""
    def value(key):
        result = snapshot.get(key)
        return 'Unavailable' if result is None else str(result)
    owned = bool(snapshot.get('owned'))
    title = snapshot.get('name') or 'Select a Picto'
    status = 'Owned' if owned else 'Locked — definition only'
    if not snapshot.get('normal', True):
        status += ' | EXPERIMENTAL'
    level = value('level') if owned else 'Unavailable (not owned)'
    mastery = value('mastery') if owned else 'Unavailable (not owned)'
    effect = f"Effect: {value('effect')}"
    if snapshot.get('effect') is None and snapshot.get('effect_references'):
        refs = [r['row'] for r in snapshot['effect_references'] if isinstance(r, dict) and isinstance(r.get('row'), str)]
        if refs:
            effect = 'Effect reference: ' + ', '.join(refs)
    lines = [title, status, f"Level: {level}", f"Mastery: {mastery}",
             f"Lumina cost: {value('cost')}",
             f"Health: {value('health')}    Defense: {value('defense')}",
             f"Speed: {value('speed')}    Critical rate: {value('critical_rate')}",
             effect, f"Acquisition: {value('acquisition')}"]
    state = snapshot.get('state', 'Ready')
    message = ' '.join(str(snapshot.get('message') or '').split())
    if len(message) > 120:
        message = message[:117].rstrip() + '...'
    lines.append(state + (': ' + message if message else ''))
    return '\n'.join(lines)
