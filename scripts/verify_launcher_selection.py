"""Offline launcher check: experimental flags must select an explicit session."""
from pathlib import Path
import runpy
import sys
from unittest.mock import patch


def main():
    namespace = runpy.run_path(str(Path(__file__).with_name('run_sdk.py')))
    launch = namespace['main']
    selected = []

    class Selected(BaseException):
        pass

    def capture(**kwargs):
        selected.append(kwargs)
        raise Selected

    for flag in ('menu-ownership', 'button-references', 'button-actions', 'multi-controls', 'traces'):
        with patch.dict(launch.__globals__, Session=capture), \
                patch.object(sys, 'argv', ['run_sdk.py', 'console', '--'+flag]), \
                patch('logging.basicConfig'), \
                patch.dict(launch.__globals__, RotatingFileHandler=lambda *a, **k: None):
            try:
                launch()
            except Selected:
                pass
            else:
                raise AssertionError('Launcher did not select an explicit session')
        assert selected[-1][flag.replace('-', '_')] is True
    print('All five menu/trace flags select an explicit session; no game attachment performed.')


if __name__ == '__main__':
    main()
