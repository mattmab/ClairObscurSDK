"""Installation paths independent of a mod's extraction/cache directory."""
from pathlib import Path


def sdk_root():
    """Root containing src, runtime, settings and build in both layouts."""
    return Path(__file__).resolve().parents[2]


def settings_dir():
    return sdk_root() / 'settings'


def logs_dir():
    return sdk_root() / 'logs'


def game_root():
    """Resolve the installed SDK layout; development callers must supply a path."""
    root = sdk_root()
    if root.name != 'SDK' or not (root.parent / 'Sandfall').is_dir():
        raise RuntimeError('Game root requires the install-directory/SDK layout')
    return root.parent
