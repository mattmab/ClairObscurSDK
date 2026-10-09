"""Small trusted mod demonstrating lifecycle-owned configurable keybinds."""
import logging
from expedition33.management import Action, Keybind, ModDefinition


class Mod:
    def __init__(self):
        self.count = 0
        self.session = None

    def management(self):
        return ModDefinition('keybind-example', 'Keybind Example',
            description='F6 counts presses through the external persistent controller. Remap in Keybinds or mods bind.',
            actions=(Action('status', 'Show press count', self.status),),
            keybinds=(Keybind('count', 'Count press', 'F6', self.count_press),
                      Keybind('error', 'Demonstrate contained error', None, self.fail)))

    def enable(self, session):
        self.session = session
        session.console.expose('keybind_example', self)

    def disable(self):
        self.session = None

    def count_press(self, _):
        if self.session is None:
            raise RuntimeError('Example is disabled')
        self.count += 1
        logging.getLogger('expedition33.keybind_example').info('Physical key callback count=%d', self.count)

    def status(self, _):
        return {'presses': self.count, 'enabled': self.session is not None}

    def fail(self, _):
        raise ValueError('Example callback error: game loop remains unaffected')
