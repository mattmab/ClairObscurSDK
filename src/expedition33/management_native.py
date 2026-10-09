"""Experimental native frontend over the shared management presenter.

Boolean and choice settings support click editing. Numeric/text/JSON editors and
key capture remain pending; submit() accepts validated typed input from a future
editor without creating separate state or bypassing Registry validation.
"""
import logging
import textwrap

from .management_view import ManagementView
from .management import ManagementError
from .widgets import OwnedMenuPanel


def display_line(text, width):
    """Bound a single visual row without changing registry metadata."""
    text = ' '.join(text.split())
    return text if len(text) <= width else text[:width - 1] + '…'


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
    def __init__(self, session, registry, *, cached_planning=False, cached_construction=False):
        if type(cached_planning) is not bool or type(cached_construction) is not bool:
            raise ValueError('Planning options must be bool')
        self._cached_planning = cached_planning
        self.view = ManagementView(registry)
        self.panel = OwnedMenuPanel(session, cached_construction=cached_construction)
        self.frame = None
        self.actions = []
        self.error = None
        self._accept_input = False
        self._logged_detail = None

    def open(self):
        self.panel.build()
        if self._cached_planning:
            self.panel.enable_cached_planning()
        self.frame = self.view.render()
        self._paint()
        self.panel.open()
        self._bind()
        return self.frame

    def _revoke(self):
        # Stop dispatch first; do not rebind while any removal is deferred.
        self._accept_input = False
        for action in self.actions:
            if not action.remove():
                raise RuntimeError('Control removal deferred; close this native menu')
        self.actions.clear()

    def _paint(self):
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

    def _bind(self):
        frame = self.frame
        for index, control in enumerate(frame.controls):
            if not control.enabled:
                continue
            def click(_event, control=control, frame=frame):
                if not self._accept_input or self.frame is not frame:
                    raise ManagementError('Native menu input is revoked or stale')
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
            self.actions.append(self.panel.menu.bind_control(self.panel.buttons[index], click))
        self._accept_input = True

    def submit(self, revision, token, **value):
        frame = self.view.activate(revision, token, **value)
        self._revoke()
        self.frame, self.error = frame, None
        if frame.closed:
            return self.close()
        self._paint()
        self._bind()
        return frame

    def refresh(self):
        self._revoke()
        self.frame = self.view.render()
        self._paint()
        self._bind()
        return self.frame

    def close(self):
        self._accept_input = False
        self.view.close()
        # Panel's native close revokes every registration, including any whose
        # partial bind/removal did not return a usable Python handle.
        result = self.panel.close()
        if result:
            self.actions.clear()
        return result
