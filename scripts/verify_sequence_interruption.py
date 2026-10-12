"""Two-phase, no-play ownership test, driven through the native game console.

begin(mod), close console and Escape the menu, then finish() from the console.
The test never plays a sequence or writes game saves.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from expedition33.sequences import OwnedLevelSequence

ROOT = Path(__file__).resolve().parents[1]
SAVES = Path('C:/Users/Matt/AppData/Local/Sandfall/Saved/SaveGames')

def hashes():
    return {str(p.relative_to(SAVES)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in SAVES.rglob('*.sav')}

def begin(mod):
    global sequence, scope, report
    scope = mod.session
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'pid': scope.pid,
              'playback_attempted': False, 'before_hashes': hashes(),
              'leases_before': repr(scope._session._lease_command('lease-status'))}
    sequence = OwnedLevelSequence(scope)
    sequence.build(mod.native.menu.panel,
        '/Game/Cinematics/Titles/SequenceTitles/LS_Title_PrologueLumiere.LS_Title_PrologueLumiere')
    report['armed'] = sequence.owner.status()
    report['status'] = sequence.status()
    report['leases_created'] = repr(scope._session._lease_command('lease-status'))
    return report['status']

def finish():
    try:
        report['native_after_menu_close'] = sequence.owner.status()
        # The menu must have caused native cleanup before Python calls close.
        report['native_interruption_confirmed'] = report['native_after_menu_close'] == 'closed'
    finally:
        sequence.close()
    report['leases_after'] = repr(scope._session._lease_command('lease-status'))
    report['after_hashes'] = hashes()
    report['save_hashes_unchanged'] = report['before_hashes'] == report['after_hashes']
    path = ROOT / ('evidence/sequence-interruption-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S') + '.json')
    path.write_text(json.dumps(report, indent=2), encoding='utf8')
    return {k: v for k, v in report.items() if not k.endswith('_hashes')}
