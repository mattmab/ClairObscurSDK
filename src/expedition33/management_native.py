"""Experimental native frontend over the shared management presenter.

Boolean and choice settings support click editing. Numeric/text/JSON editors and
key capture remain pending; submit() accepts validated typed input from a future
editor without creating separate state or bypassing Registry validation.
"""
from .frontend_rejection import known_rejection
import logging
import textwrap
from functools import lru_cache
from ._menu_latency import MenuLatency, measure_method
from contextlib import nullcontext

from .management_view import ManagementView
from .management import ManagementError
from .widgets import OwnedMenuPanel
from ._reader import ReadBatch


@lru_cache(maxsize=256)
def display_line(text, width):
    """Bound a single visual row without changing registry metadata."""
    text = ' '.join(text.split())
    return text if len(text) <= width else text[:width - 1] + '…'


@lru_cache(maxsize=128)
def display_detail(text, *, width=42, height=18):
    """Explicit newlines for the current base TextBlock; full results stay logged.

    Character bounds are an initial layout budget, not native font metrics.
    Responsive sizing and native scrolling remain separate frontend work.
    """
    lines = []
    for paragraph in text.splitlines():
        lines.extend(textwrap.wrap(paragraph, width=width) or [''])
    if len(lines) > height:
        lines = lines[:height - 1] + ['… More text in the SDK log.']
    return '\n'.join(lines)


class NativeManagementMenu:
    def __init__(self, session, registry, *, cached_planning=False, cached_construction=False, selected_results=False, read_batches=False, reusable=False, view_factory=ManagementView, panel_factory=None):
        if type(cached_planning) is not bool or type(cached_construction) is not bool:
            raise ValueError('Planning options must be bool')
        self.latency = MenuLatency()
        self._button_colors = {}
        self._cached_planning = cached_planning
        if type(read_batches) is not bool:
            raise ValueError('read_batches must be bool')
        self._read_batches = read_batches
        self._reusable = reusable
        self._view_factory = view_factory
        self.view = view_factory(registry)
        self.panel = (panel_factory or OwnedMenuPanel)(session, cached_construction=cached_construction,
                                    selected_results=selected_results)
        self.frame = None
        self.actions = []
        self.error = None
        self.failure = None
        self._frontend_rejection = None
        self._accept_input = False
        self._feedback_binding_frame = None
        self._presentation_suspended = False
        self._presentation_dirty = False
        self._logged_detail = None

    def prepared_view_state(self):
        from .mods_workspace import ModsWorkspaceView
        from .mods_workspace_scroll import ScrollWorkspaceView
        from .title_management import TitleWorkspaceView
        if type(self.view) not in (ManagementView,ModsWorkspaceView,ScrollWorkspaceView,TitleWorkspaceView):
            # Mod presenters can own Sessions, workers, or callbacks. They are
            # not copyable navigation state. Repaint on explicit open instead
            # of traversing arbitrary mod resources for the prepared-frame key.
            return None
        from copy import deepcopy
        return (type(self.view),id(self.view),deepcopy({k:v for k,v in vars(self.view).items() if k!='registry'}))

    @measure_method('menu.open_total')
    def open(self):
        # A prepared tree already has metadata and menu call plans. Starting a
        # read-worker process on this hot path would add a new startup delay.
        with self._read_operation() if self.panel.state == 'new' else nullcontext():
            return self._open()

    def _read_operation(self):
        if self._read_batches and self.panel.state != 'closed':
            return ReadBatch(self.panel.scope.pid)
        return nullcontext()

    def _open(self):
        if self.panel.state == 'new':
            self.prepare()
        if self.panel.state != 'built':
            raise ManagementError('Menu is not prepared for opening')
        if self.view.closed:
            self.view = self._view_factory(self.view.registry)
        reuse=getattr(self,'_reuse_prepared_frame',False) and not self.view.closed
        self._reuse_prepared_frame=False
        if not reuse:
            self.frame = self._render_view()
            self._paint()
        self.panel.open()
        self._bind()
        return self.frame

    @measure_method('menu.detached_prepare')
    def prepare(self):
        """Build and paint while detached, before reporting UI readiness."""
        self.panel.build()
        if self._cached_planning:
            self.panel.enable_cached_planning()
        self.frame = self._render_view()
        self._paint()
        if self._reusable:
            self.panel.prime_menu_plan()
        return self.frame

    @measure_method('menu.presenter_render')
    def _render_view(self):
        return self.view.render()

    def _revoke(self):
        # Stop dispatch first; do not rebind while any removal is deferred.
        self._accept_input = False
        self._feedback_binding_frame = None
        if self.actions:
            if not self.panel.menu.remove_controls(self.actions):
                raise RuntimeError('Control removal deferred; close this native menu')
        self.actions.clear()

    def _paint(self, *, presentation_restore=False):
        if self._presentation_suspended and not presentation_restore:
            self._presentation_dirty = True
            return
        try:
            with self.latency.measure('menu.paint_total'):
                with self.panel.paint_batch():
                    self._paint_frame()
        except BaseException:
            # Queued caches are tentative until the native paint batch returns.
            self._button_colors.clear()
            raise

    def _set_button_color(self,index,color):
        value=tuple(color)
        if self._button_colors.get(index)==value:
            self.latency.count('paint.color_cache_hits');return
        self.panel._render_call(self.panel.buttons[index],'Button','SetBackgroundColor',
            InBackgroundColor=dict(zip(('R','G','B','A'),(*value,1.))))
        self._button_colors[index]=value
        self.latency.count('paint.color_setters')

    def _paint_frame(self):
        frame = self.frame
        self.panel.set_text(self.panel.title,
            f'{display_line(frame.title, 64)}   ({frame.page + 1}/{frame.pages})')
        detail = '\n\n'.join(filter(None, (self.error, frame.status, frame.description)))
        if detail != self._logged_detail:
            logging.getLogger(__name__).info('Native menu %s: %s', frame.title, detail)
            self._logged_detail = detail
        self.panel.set_text(self.panel.detail, display_detail(detail))
        for index in range(self.panel.count):
            control = frame.controls[index] if index < len(frame.controls) else None
            self.panel.set_text(self.panel.labels[index], display_line(control.label, 48) if control else '')
            self.panel.set_enabled(index, bool(control and control.enabled))
            self.panel.set_visible(index, control is not None)

    @measure_method('menu.bind_controls')
    def _bind(self):
        frame = self.frame
        bindings = []
        for index, control in enumerate(frame.controls):
            if not control.enabled:
                continue
            def click(_event, control=control, frame=frame):
                # Render-opacity suspension retains native focus/input lifetime.
                # Invisible controls must consume clicks without invoking mods.
                if self._presentation_suspended:
                    return
                if not self._accept_input or (self.frame is not frame and self._feedback_binding_frame is not frame):
                    raise ManagementError('Native menu input is revoked or stale')
                current=next((c for c in self.frame.controls if c.token==control.token),None)
                if current is None or not current.enabled:return
                editor = control.editor
                if editor is None or editor.kind == 'json':
                    self.submit(frame.revision, control.token)
                elif editor.kind == 'bool':
                    self.submit(frame.revision, control.token, value=not editor.value)
                elif editor.kind == 'choice' and editor.choices:
                    current = next(i for i, value in enumerate(editor.choices)
                                   if type(value) is type(editor.value) and value == editor.value)
                    self.submit(frame.revision, control.token,
                                value=editor.choices[(current + 1) % len(editor.choices)])
                else:
                    self.error = 'Native text/numeric editor pending. Use mods set in the console.'
                    self._paint()
            bindings.append((self.panel.buttons[index], click))
        self.actions.extend(self.panel.menu.bind_controls(bindings))
        self._accept_input = True

    def update_control_feedback(self, controls):
        """Paint labels/disable controls without invalidating captured pointer input.

        Navigation and new actions still require refresh/rebinding. Feedback may
        only keep or disable existing actions, with the same tokens and editors.
        """
        from dataclasses import replace
        controls=tuple(controls);previous=self.frame
        if len(controls)!=len(previous.controls) or any(
                a.token!=b.token or a.editor!=b.editor or (b.enabled and not a.enabled)
                for a,b in zip(previous.controls,controls)):
            raise ManagementError('Feedback cannot add or enable menu actions')
        if self._feedback_binding_frame is None:self._feedback_binding_frame=previous
        for index,(a,b) in enumerate(zip(previous.controls,controls)):
            if a.label!=b.label:self.panel.set_text(self.panel.labels[index],b.label)
            if a.enabled!=b.enabled:self.panel.set_enabled(index,b.enabled)
        self.frame=replace(previous,controls=controls)

    def submit(self, revision, token, **value):
        if self.failure:
            raise ManagementError('Native menu failed; dispose it before reopening: ' + self.failure)
        frame = self.view.activate(revision, token, **value)
        try:
            if frame.closed:
                self.frame, self.error = frame, None
                return self.hide() if self._reusable else self.close()
            if self._presentation_suspended:
                # The action may have just started playback. Keep native action
                # ownership untouched until presentation cleanup completes.
                self.frame, self.error = frame, None
                self._presentation_dirty = True
                return frame
            self._revoke()
            self.frame, self.error = frame, None
            self._paint()
            self._bind()
            return frame
        except BaseException as error:
            self._accept_input = False
            self._frontend_rejection = known_rejection(error) or getattr(self,'_frontend_rejection',None)
            self.failure = f'{type(error).__name__}: {error}'
            raise

    @measure_method('menu.refresh_detached')
    def refresh_detached(self):
        if (self.panel.state != 'built' or self.panel.menu is not None
                or any(getattr(action,'active',False) for action in self.actions)):
            raise ManagementError('Detached refresh requires acknowledged native detach')
        if self._presentation_suspended:
            raise ManagementError('Detached refresh cannot replace a suspended presentation')
        self._accept_input = False
        if self.view.closed:
            self.view = self._view_factory(self.view.registry)
        self.frame = self._render_view()
        self._paint()
        return self.frame

    @measure_method('menu.refresh')
    def refresh(self):
        if self._presentation_suspended:
            self.frame = self._render_view()
            self._presentation_dirty = True
            return self.frame
        self._revoke()
        self.frame = self._render_view()
        self._paint()
        self._bind()
        return self.frame

    def _restore_presentation_frame(self):
        """Flush the latest deferred frame while visuals/callbacks remain gated."""
        if not self._presentation_suspended:
            raise ManagementError('Presentation frame restore requires suspended input')
        if self.failure:
            raise ManagementError('Menu refresh failed; preserve owner for cleanup: ' + self.failure)
        if not self._presentation_dirty:
            return
        try:
            self._revoke()
            self._paint(presentation_restore=True)
            self._bind()
            self._presentation_dirty = False
        except BaseException as error:
            self._accept_input = False
            self._frontend_rejection = known_rejection(error) or getattr(self,'_frontend_rejection',None)
            self.failure = f'{type(error).__name__}: {error}'
            raise

    def hide(self):
        self._accept_input = False
        suspend = getattr(self.view, 'suspend_frame', None)
        if callable(suspend) and not self.view.closed and not self.frame.closed:
            self.frame = suspend(self.frame)
        else:
            self.view.close()
        if not self.panel.hide():
            return False
        self.actions.clear()
        return True

    def retire_world(self, *, native_retirement_ack=False):
        self._accept_input=False
        result=self.panel.retire_world(native_retirement_ack=native_retirement_ack)
        if result=='ack':
            self.actions.clear()
            # No view.close(): some views route that into model.stop().
            if hasattr(self.view,'closed'):self.view.closed=True
        return result

    def close(self):
        with self._read_operation():
            return self._close()

    def _close(self):
        self._accept_input = False
        self.view.close()
        # Panel's native close revokes every registration, including any whose
        # partial bind/removal did not return a usable Python handle.
        # Explicit owned-tree contract: detach input, clear/read back RootWidget,
        # then release the wholly owned hierarchy without per-child removals.
        # Custom/legacy panels retain their ordinary close contract.
        close_owned = getattr(self.panel, 'close_owned_tree', None)
        result = close_owned() if callable(close_owned) else self.panel.close()
        if result:
            self.actions.clear()
        return result
