"""Query a small menu focus sample through the existing owner-thread file service.

No console opening, input injection, setters, or new controller is performed.
Request/response files remain as evidence; a timeout never replays a request.
"""
import json
import os
from pathlib import Path
import time
import uuid

from expedition33.catalog import capture

ROOT = Path(__file__).resolve().parents[1]


def main():
    data = ROOT / 'settings/E33Introspection'
    status = json.loads((data / 'status.json').read_text())
    assert status['enabled'] and time.time() - status['heartbeat'] < 10
    catalog = capture()
    assert catalog.pid == status['target_pid']
    players = [o for o in catalog.select('PlayerController') if not o.object_flags & 0x10]
    assert len(players) == 1
    player = {'$object': catalog.path_name(players[0])}
    prior = json.loads((ROOT / 'evidence/main-menu-focus.json').read_text())
    assert prior['pid'] == catalog.pid and prior['complete']
    names = {'ContinueButton', 'NewGameButton', 'SettingsButton', 'QuitButton', 'InternalRootButtonBase'}
    paths = [row['path'] for row in prior['widgets'] if row['name'] in names]
    assert 1 <= len(paths) <= 12
    evidence = dict(pid=catalog.pid, session=status['session'], read_only=True,
                    console_opened=False, complete=False, widgets=[], requests=[])
    output = ROOT / 'evidence/menu-focus-via-harness.json'
    def save():
        output.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    save()
    for path in paths:
        catalog.find_path(path, 'Widget')
        row = dict(path=path)
        evidence['widgets'].append(row)
        for member, key in (('HasKeyboardFocus', 'keyboard'), ('HasUserFocus', 'user')):
            current = json.loads((data / 'status.json').read_text())
            assert current['session'] == status['session'] and current['enabled']
            request_id = uuid.uuid4().hex
            request = dict(session=status['session'], expires=time.time()+120,
                           op='invoke', target={'$object': path}, member=member,
                           args={'PlayerController': player} if key == 'user' else {},
                           allow_mutation=True)
            evidence['requests'].append(dict(id=request_id, path=path, member=member))
            save()
            target = data / 'requests' / (request_id + '.json')
            temporary = target.with_suffix('.tmp')
            temporary.write_text(json.dumps(request), encoding='utf-8')
            os.replace(temporary, target)
            response = data / 'responses' / target.name
            deadline = time.monotonic()+120
            while not response.exists():
                if time.monotonic() >= deadline:
                    raise TimeoutError(f'Unresolved request {request_id}; do not replay')
                time.sleep(.2)
            reply = json.loads(response.read_text())
            assert reply['id'] == request_id and reply['session'] == status['session']
            assert reply['ok'], reply
            assert type(reply['result']) is bool, reply
            row[key] = reply['result']
            save()
        print(row, flush=True)
    evidence['complete'] = True
    save()


if __name__ == '__main__':
    main()
