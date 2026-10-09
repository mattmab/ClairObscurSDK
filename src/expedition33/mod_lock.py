"""Cooperative process ownership for a mod root; the lock file is never deleted."""
import os
from pathlib import Path


class ModRootLock:
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        path = self.root / '.sdk-loader.lock'
        if path.is_symlink() or path.is_junction():
            raise RuntimeError('Mod root lock file is redirected')
        self.stream = path.open('a+b', buffering=0)
        try:
            if self.stream.seek(0, 2) == 0:
                self.stream.write(b'\0')
            self.stream.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            self.stream.close()
            raise RuntimeError('Mod root is already owned or cannot be locked: ' + str(self.root)) from None

    def close(self):
        # Closing the handle releases the OS lock, including on process death.
        # Removing the file would allow two handles to lock different files.
        self.stream.close()
