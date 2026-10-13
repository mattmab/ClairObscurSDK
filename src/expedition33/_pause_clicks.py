"""One native click observer shared by independently owned pause entries."""
from . import _traces


class PauseClicks:
    def __init__(self, session, function, button, catalog):
        self.session = session
        self.key = (button.pid, button.index, button.serial)
        self.closed = False
        hub = getattr(session, '_pause_click_hub', None)
        if hub is None:
            trace = _traces.start(session, function, button, duration_ms=300000,
                                  limit=1000, catalog=catalog)
            hub = {'trace': trace, 'queues': {}, 'function': function}
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
        queues = self.hub['queues']
        for event in self.hub['trace'].read() if poll else ():
            key = (event.pid, event.index, event.serial)
            if key in queues:
                if len(queues[key]) >= 64:
                    raise RuntimeError('Pause click delivery overflow')
                queues[key].append(event)
        result = tuple(queues[self.key])
        queues[self.key].clear()
        return result

    def renew(self):
        return self.hub['trace'].renew()

    def close(self):
        if self.closed:
            return
        if len(self.hub['queues']) == 1:
            self.hub['trace'].close()
            self.session._pause_click_hub = None
        del self.hub['queues'][self.key]
        self.closed = True
