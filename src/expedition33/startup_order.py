"""Persisted optional-mod order; core bootstrap remains owned by the host."""
import json
import logging
from .settings import identifier

DEFAULT_ORDER = ('e33.world-builder', 'e33.map-overlays')

class StartupOrder:
    def __init__(self, path):
        self.path = path
    def read(self):
        if not self.path.exists():
            self.save(DEFAULT_ORDER)
            return list(DEFAULT_ORDER)
        try:
            data = json.loads(self.path.read_text(encoding='utf8'))
            order = data['order']
            if data.get('version') != 1 or type(order) is not list or len(order)>1024 or len(set(order))!=len(order):
                raise ValueError('Invalid startup order')
            for key in order: identifier(key)
            return order
        except (ValueError, TypeError, KeyError) as error:
            logging.getLogger(__name__).warning('Invalid startup-order.json; using defaults: %s',error)
            return list(DEFAULT_ORDER)
    def save(self, order):
        order = list(order)
        if len(order)>1024 or len(set(order))!=len(order):raise ValueError('Invalid startup order')
        for key in order:identifier(key)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        tmp=self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps({'version':1,'order':order},indent=2)+'\n',encoding='utf8')
        tmp.replace(self.path)
    def ordered(self, ids):
        ids=list(dict.fromkeys(ids));available=set(ids)
        result=[key for key in self.read() if key in available]
        result.extend(key for key in ids if key not in result)
        # Map Overlays calls the World Builder API. Preserve that dependency
        # even if a hand-edited file places the companion first.
        builder,overlay=DEFAULT_ORDER
        if builder in result and overlay in result and result.index(builder)>result.index(overlay):
            result.remove(builder);result.insert(result.index(overlay),builder)
        return result

class StartupGate:
    """Give an enabled mod bounded polling time before the next enable."""
    def __init__(self):self.callback=None;self.deadline=0
    def arm(self, mod, now):
        self.callback=getattr(mod,'startup_pending',None)
        self.deadline=now+10.
    def pending(self, now):
        if self.callback is None:return False
        if now<self.deadline:
            try:
                if self.callback():return True
            except Exception:
                logging.getLogger(__name__).exception('Startup readiness check failed')
        self.callback=None
        return False
