"""One native click observer shared by independently owned pause entries."""
from . import _traces
import time


class PauseClicks:
    def __init__(self, session, function, button, catalog):
        self.session = session
        self.key = (button.pid, button.index, button.serial)
        self.closed = False
        self.function, self.button, self.catalog = function, button, catalog
        hub = getattr(session, '_pause_click_hub', None)
        if hub is None:
            trace = _traces.start(session, function, button, duration_ms=300000,
                                  limit=1000, catalog=catalog)
            hub = {'trace': trace, 'queues': {}, 'function': function,
                   'renew_at': time.monotonic() + 120, 'renew_count': 900}
            session._pause_click_hub = hub
        if hub['function'] != function or self.key in hub['queues']:
            raise RuntimeError('Pause click observer identity conflict')
        self.hub = hub
        hub['queues'][self.key] = []

    @property
    def state(self):
        return self.hub['trace'].state

    @property
    def _observed(self):
        return self.hub['trace']._observed

    def read(self, *, poll=True):
        """Drain this subscription, optionally using an already-polled hub.

        A group of controls sharing this hub polls its first subscription once;
        the remaining subscriptions drain their routed queues with poll=False.
        """
        if self.closed:
            raise RuntimeError('Pause click subscription is closed')
        if poll:
            self.recover()
        queues = self.hub['queues']
        for event in self.hub['trace'].read() if poll else ():
            key = (event.pid, event.index, event.serial)
            if key in queues:
                if len(queues[key]) >= 64:
                    raise RuntimeError('Pause click delivery overflow')
                queues[key].append(event)
        if poll:
            self.recover()
            if (time.monotonic() >= self.hub['renew_at'] or
                    self._observed >= self.hub['renew_count']):
                self.renew()
        result = tuple(queues[self.key])
        queues[self.key].clear()
        return result

    def renew(self):
        result = self.hub['trace'].renew()
        self.hub['renew_at'] = time.monotonic() + 120
        self.hub['renew_count'] = self._observed + 900
        return result

    def recover(self):
        """Replace only a confirmed terminal observation, never an unknown call."""
        trace = self.hub['trace']
        if trace.state not in ('expired', 'capped'):
            return
        trace.close()
        self.hub['trace'] = _traces.start(self.session, self.function, self.button,
            duration_ms=300000, limit=1000, catalog=self.catalog)
        self.hub['renew_at'] = time.monotonic() + 120
        self.hub['renew_count'] = 900

    def close(self):
        if self.closed:
            return
        if len(self.hub['queues']) == 1:
            self.hub['trace'].close()
            self.session._pause_click_hub = None
        del self.hub['queues'][self.key]
        self.closed = True
