"""Small real mod demonstrating shared settings, actions and scoped native hooks."""
from expedition33.management import ModDefinition, Option, Action


class Mod:
    def __init__(self):
        self.session = None
        self.label = 'Actor observation'
        self.events = 0

    def management(self):
        return ModDefinition('example.management', 'Management Example', version='0.1',
            description='Reads the verified Actor getter and observes its scoped hook.',
            options=(Option('label', 'Observation label', 'text', self.label, on_change=self.set_label),),
            actions=(Action('observe', 'Observe default Actor', self.observe),))

    def set_label(self, value):
        self.label = value

    def enable(self, session):
        self.session = session
        self.actor = session.find_object('Default__Actor')
        session.hook(self.actor, 'Actor.IsActorBeingDestroyed', self.on_event)

    def on_event(self, context):
        self.events += 1

    def observe(self, argument):
        result = self.session.call(self.actor, 'Actor.IsActorBeingDestroyed')
        return {'label': self.label, 'is_actor_being_destroyed': result}

    def disable(self):
        self.session = None
        self.actor = None
