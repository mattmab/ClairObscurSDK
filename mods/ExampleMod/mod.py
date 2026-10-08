"""Harmless user-triggered getter observation using only the public SDK API."""
import logging
from expedition33 import sdk

log = logging.getLogger('expedition33.mods.ExampleMod')


class Mod:
    def __init__(self):
        self.hook = None

    def enable(self, session: sdk.Session):
        actor = session.find_object('Default__Actor')
        self.hook = session.hook(actor, 'Actor.IsActorBeingDestroyed', self.on_getter)
        result = session.call(actor, 'Actor.IsActorBeingDestroyed')
        log.info('Called %s.IsActorBeingDestroyed: %s', actor.name, result)
        session.poll()

    def on_getter(self, context):
        log.info('Observed %s.%s -> %s (object index %d)', context.object.name,
                 context.target, context.result, context.object.index)

    def disable(self):
        if self.hook is not None:
            self.hook.remove()
            self.hook = None
