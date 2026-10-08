"""Actual client -> file service -> independent reader -> live game verification."""
import json
from pathlib import Path
import subprocess
import sys
import time

from e33_introspect import send


def main():
    root = Path(__file__).resolve().parents[1]
    data = root / 'settings/E33Introspection'
    evidence = root / 'evidence'
    evidence.mkdir(exist_ok=True)
    results = []
    with (evidence / 'introspection-file-host.log').open('w', encoding='utf-8') as log:
        # Windows venv python.exe is a launcher and may spawn a different PID.
        # The isolated SDK host needs no site packages; launch the same installed
        # base interpreter directly so process ownership can be verified exactly.
        process = subprocess.Popen([sys._base_executable, '-I', '-S', '-B', str(root / 'scripts/run_sdk.py'),
            'introspection', '--console-key', 'F10', '--seconds', '25'], cwd=root,
            stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            deadline = time.monotonic() + 15
            while True:
                if process.poll() is not None:
                    raise RuntimeError('Host exited before publishing its heartbeat')
                try:
                    status = json.loads((data / 'status.json').read_text())
                    if status['enabled'] and status['controller_pid'] == process.pid:
                        break
                except (OSError, ValueError):
                    pass
                if time.monotonic() >= deadline:
                    raise TimeoutError('No matching host heartbeat')
                time.sleep(.05)
            for request in ({'op': 'status'}, {'op': 'roots'},
                            {'op': 'schema', 'class': 'Actor', 'limit': 3},
                            {'op': 'not_an_operation'}, {'op': 'status'}):
                response = send(request, data, timeout=15)
                results.append({'request': request, 'response': response})
                assert response['session'] == status['session']
                assert response['ok'] == (request['op'] != 'not_an_operation')
            assert results[1]['response']['result']['PlayerController']
            assert len(results[2]['response']['result']['properties']) == 3
            assert process.wait(timeout=35) == 0
            closed = json.loads((data / 'status.json').read_text())
            assert not closed['enabled'] and closed['session'] == status['session']
            assert not list((data / 'requests').glob('*.processing'))
            (evidence / 'introspection-file-service-live.json').write_text(json.dumps(
                {'heartbeat': status, 'requests': results, 'shutdown': closed, 'exit_code': 0}, indent=2),
                encoding='utf-8')
            print('Live file protocol passed: roots/schema, error recovery, matching session, clean host shutdown.')
        finally:
            if process.poll() is None:
                # Only our external host, never the game. Native owner-death
                # cleanup handles failure; this does not retry pending requests.
                process.kill()
                process.wait(timeout=10)


if __name__ == '__main__': main()
