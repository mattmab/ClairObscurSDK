"""Import the portable image pack using this installation's cache keys."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


def game_files(game):
    return [game / 'Sandfall/Binaries/Win64/SandFall-Win64-Shipping.exe'] + sorted(
        p for p in (game / 'Sandfall/Content/Paks').glob('*') if p.suffix in ('.utoc', '.pak'))


def identity(game):
    files = game_files(game)
    return {'executable_sha256': hashlib.sha256(files[0].read_bytes()).hexdigest(),
            'containers': [[p.name, p.stat().st_size] for p in files[1:]]}


def build_key(game):
    return hashlib.sha256(repr([(p.name, p.stat().st_size, p.stat().st_mtime_ns)
                               for p in game_files(game) if p.exists()]).encode()).hexdigest()


def import_pack(pack, game):
    manifest = json.loads((pack / 'thumbnails.json').read_text(encoding='utf8'))
    if manifest.get('version') != 1 or manifest['game'] != identity(game):
        raise ValueError('This thumbnail pack is for a different game build.')
    # Validate the entire pack before writing anything. Only content-addressed
    # filenames are accepted; no archive-supplied destination paths are used.
    for asset, digest in manifest['images'].items():
        if not asset.startswith('/Game/') or not re.fullmatch('[0-9a-f]{64}', digest):
            raise ValueError('Invalid thumbnail mapping')
        data = (pack / 'images' / (digest + '.png')).read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError('Thumbnail checksum mismatch: ' + asset)
    key = build_key(game)
    root = game / 'SDK/settings/E33WorldBuilder/cache/neutral-v1'
    root.mkdir(parents=True, exist_ok=True)
    written = 0
    for asset, digest in manifest['images'].items():
        target = root / (hashlib.sha256((key + ':neutral-v1b:' + asset).encode()).hexdigest() + '.png')
        if target.exists():
            continue  # Preserve locally regenerated pictures.
        temporary = target.with_suffix('.import-tmp')
        temporary.write_bytes((pack / 'images' / (digest + '.png')).read_bytes())
        temporary.replace(target)
        written += 1
    # Let the game enumerate its own catalog; importing images doesn't replace
    # catalog metadata, personal maps, or capture preferences.
    return {'imported': written, 'already_present': len(manifest['images']) - written}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, required=True)
    args = parser.parse_args()
    game = args.game.resolve()
    sys.path.insert(0, str(game / 'SDK/src'))
    from expedition33.mod_lock import ModRootLock
    lock = ModRootLock(game / 'SDK')
    try:
        print(json.dumps(import_pack(Path(__file__).resolve().parent, game)))
    finally:
        lock.close()
