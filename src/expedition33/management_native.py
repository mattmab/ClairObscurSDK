"""Experimental native frontend over the shared management presenter.

Boolean and choice settings support click editing. Numeric/text/JSON editors and
key capture remain pending; submit() accepts validated typed input from a future
editor without creating separate state or bypassing Registry validation.
"""
from .management_view import ManagementView
from .management import ManagementError
from .widgets import OwnedMenuPanel


class NativeManagementMenu:
    def __init__(self, session, registry):
        self.view = ManagementView(registry)
        self.panel = OwnedMenuPanel(session)
        self.frame = None
        self.actions = []
        self.error = None
        self._accept_input = False

    def open(self):
        self.panel.build()
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
            f'{frame.title}   ({frame.page + 1}/{frame.pages})')
        self.panel.set_text(self.panel.detail, '\n\n'.join(filter(None,
            (frame.description, frame.status, self.error))))
        for index in range(self.panel.count):
            control = frame.controls[index] if index < len(frame.controls) else None
            self.panel.set_text(self.panel.labels[index], control.label if control else '')
            self.panel.set_enabled(index, bool(control and control.enabled))

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
