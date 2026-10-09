"""Bridge the original Harness trace request contract to owned SDK traces."""
from collections import deque
import time
from .core import bounded


class TraceAdapter:
    def __init__(self, explorer):
        self.explorer = explorer
        self.handles = {}

    def start(self, request):
        explorer, backend = self.explorer, self.explorer.sdk
        name, path = str(request['name']), str(request['function'])
        if name in explorer.traces or len(explorer.traces) >= 16:
            raise ValueError('Trace name exists or 16 trace limit reached; trace_stop with forget first')
        function = backend.find_object('Function', path)._observed
        target = explorer.resolve(request['target'])._observed if request.get('target') else None
        if target is not None:
            exemplar = target
        else:
            candidates = (obj for obj in backend.catalog.objects
                          if function.outer_index in backend.catalog.ancestors(obj.class_index))
            exemplar = next(candidates, None)
            if exemplar is None:
                raise ValueError('No live compatible exemplar for trace registration')
        cap, seconds = bounded(request.get('limit'), 100, 1000), bounded(request.get('seconds'), 30, 300)
        handle = backend.session.trace(function, exemplar, target=target, duration_ms=seconds * 1000, limit=cap)
        self.handles[name] = handle
        explorer.traces[name] = dict(path=path, active=True, count=0, events=deque(maxlen=cap),
            deadline=time.monotonic() + seconds, observed=0, dropped=0, rejected=0)
        return dict(name=name, limit=cap, seconds=seconds)

    def poll(self, name=None, *, batches=1):
        explorer, backend = self.explorer, self.explorer.sdk
        names = (name,) if name is not None else tuple(self.handles)
        for key in names:
            handle, trace = self.handles[key], explorer.traces[key]
            for _ in range(batches):
                events = handle.read()
                if events and backend.catalog is None:
                    backend.refresh()
                for event in events:
                    obj = backend.catalog.by_index.get(event.index)
                    if obj is not None and obj.pid == event.pid and obj.serial == event.serial:
                        target = explorer.ref(backend.wrap(obj))
                    else:
                        target = {'$stale_object': dict(pid=event.pid, index=event.index, serial=event.serial)}
                    trace['events'].append(dict(sequence=event.sequence, time=time.time(),
                        time_basis='delivery', native_monotonic_ms=event.monotonic_ms,
                        target_resolution='drain_time', target=target,
                        args=explorer.encode(dict(event.arguments)), return_value=explorer.encode(event.return_value)))
                    trace['events'][-1]['return'] = trace['events'][-1].pop('return_value')
                    trace['count'] += 1
                if len(events) < 8:
                    break
            status = handle.status()
            trace.update(active=handle.state == 'active', observed=status.observed,
                         dropped=status.dropped, rejected=status.rejected)

    def stop(self, name):
        self.handles[name].stop()
        self.explorer.traces[name]['active'] = False

    def read(self, request):
        name = request['name']
        if request['op'] == 'trace_stop':
            self.stop(name)
        self.poll(name, batches=8)
        trace = self.explorer.traces[name]
        result = {key: trace[key] for key in ('active', 'count', 'observed', 'dropped', 'rejected')}
        result['events'] = list(trace['events'])
        if request['op'] == 'trace_stop' and request.get('forget'):
            self.handles[name].close()
            del self.handles[name]
            del self.explorer.traces[name]
        return result

    def close(self):
        failures = []
        for name, handle in tuple(self.handles.items()):
            try:
                handle.close()
                self.explorer.traces[name]['active'] = False
                del self.handles[name]
            except Exception as error:
                failures.append(error)
        if failures:
            raise failures[0]
