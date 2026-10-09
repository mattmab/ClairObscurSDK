"""Real-click registry integration on one owned native button; no gameplay required."""
import json
from pathlib import Path
import runpy
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from expedition33 import sdk
from expedition33.mods import ModLoader

MOD = '''from expedition33.management import Action, ModDefinition
class Mod:
 def __init__(self): self.calls = []
 def management(self):
  return ModDefinition('specimen.native', 'Native registry specimen',
   actions=(Action('record', 'Record click', self.record),))
 def enable(self, session): self.session = session
 def disable(self): self.session = None
 def record(self, argument):
  self.calls.append(argument)
  return len(self.calls)
'''


def run(session):
    directory = ROOT / 'evidence' / ('management-button-' + uuid.uuid4().hex)
    mod_dir = directory / 'mods' / 'Specimen'
    mod_dir.mkdir(parents=True)
    (mod_dir / 'mod.py').write_text(MOD, encoding='utf-8')
    progress = ROOT / 'evidence/management-button-progress.json'
    evidence = {'passed': False, 'phase': 'preparing', 'directory': str(directory),
                'pid': session.pid, 'keyboard_tested': False}
    def save():
        text = json.dumps(evidence, indent=2)
        progress.write_text(text, encoding='utf-8')
        (directory / 'result.json').write_text(text, encoding='utf-8')
    save()
    loader = ModLoader(directory / 'mods', session=session)
    observe = runpy.run_path(str(ROOT / 'scripts/inspect_slate_focus_dispatch.py'))['observe']
    before = observe()
    assert before['users'][0]['matches_game_viewport']

    class Lifecycle:
        menu = None
        action = None
        def bind(self):
            self.action = self.menu.bind_action(loader.registry.action_callback(
                loader.registry.select('specimen.native'), 'record', {'source': 'native button'}))
        def open(self, scope, widget, button, player):
            self.menu = scope.prepare_menu(widget, button, player)
            assert self.menu.attach() and self.menu.focus()
            self.bind()
        def close(self):
            if self.menu is not None:
                assert self.menu.close()
                assert not self.action.active
                restored = observe()
                assert restored['users'][0]['matches_game_viewport']
                assert restored['game_viewport'] == before['game_viewport']
                evidence['focus_restored'] = True
                save()
    lifecycle = Lifecycle()

    def await_click(phase, predicate):
        evidence['phase'] = phase
        save()
        deadline = time.monotonic() + 180
        while not predicate() and time.monotonic() < deadline:
            session.poll()
            time.sleep(.05)
        assert predicate(), 'Input timeout: ' + phase

    def interact(*_):
        original = loader._loaded['Specimen'][1]
        await_click('awaiting_original_click', lambda: len(original.calls) == 1)
        assert original.calls == [{'source': 'native button'}]
        evidence['original_calls'] = original.calls[:]
        loader.unload('Specimen')
        loader.load('Specimen')
        loader.enable('Specimen')
        replacement = loader._loaded['Specimen'][1]
        await_click('awaiting_stale_click', lambda: bool(lifecycle.action.failures))
        assert 'Stale mod selection' in lifecycle.action.failures[-1]
        assert len(original.calls) == 1 and replacement.calls == []
        evidence['stale_rejected'] = True
        evidence['stale_failure'] = lifecycle.action.failures[-1]
        assert lifecycle.action.remove()
        lifecycle.bind()
        await_click('awaiting_rebound_click', lambda: len(replacement.calls) == 1)
        assert replacement.calls == [{'source': 'native button'}]
        assert not lifecycle.action.failures
        evidence['replacement_calls'] = replacement.calls[:]
        evidence['phase'] = 'cleaning'
        save()
        return {'registry_dispatch': True, 'stale_rejected': True, 'rebound_dispatch': True}

    try:
        loader.load('Specimen')
        loader.enable('Specimen')
        result = runpy.run_path(str(ROOT / 'scripts/verify_live_widget_visible.py'))['run'](
            session, activatable=True, button_enabled=True, native_lifecycle=lifecycle,
            on_display=interact, hold_seconds=0, label_text='SDK MOD ACTION - click',
            label_hit_test_invisible=True, evidence_name='management-button-widget-live.json')
        assert result['passed'] and result['holder_baseline_restored']
        evidence['holder_baseline_restored'] = True
    finally:
        loader.close()
        evidence['loader_closed'] = True
        save()
    assert not loader.status()
    evidence.update(passed=True, phase='complete')
    save()
    print('Native registry action, stale-click rejection, rebind and exact cleanup passed.')
    return evidence


if __name__ == '__main__':
    with sdk.Session(button_actions=True) as session:
        run(session)
