"""Build all current mods as deterministic .sdkmod archives without importing them."""
import argparse
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
archive = runpy.run_path(str(ROOT / 'src/expedition33/mod_archive.py'))


def build_all(source, destination, *, include=None):
    source, destination = Path(source).resolve(strict=True), Path(destination).resolve()
    if destination.is_relative_to(source):
        raise ValueError('Archive destination must be outside mod sources')
    # Prepare and validate every payload before creating the output directory.
    payloads = []
    for entry in sorted(source.glob('*/mod.py')):
        if include is not None and entry.parent.name not in include:
            continue
        data, candidate = archive['build_bytes'](entry.parent)
        payloads.append((entry.parent.name, data, candidate.summary()))
    if not payloads:
        raise ValueError('No mod entry points found')
    if include is not None and {name for name, _, _ in payloads} != set(include):
        raise ValueError('Requested mod source missing')
    destination.mkdir(parents=True, exist_ok=False)
    result = []
    for name, data, summary in payloads:
        filename = name + '.sdkmod'
        (destination / filename).write_bytes(data)
        # Validate the actual on-disk archive, including all resource hashes.
        actual = archive['read_candidate'](destination / filename, summary['sha256'])
        if actual.summary() != summary:
            raise ValueError('Archive verification changed: ' + filename)
        result.append(dict(folder=name, archive=filename, **summary))
    manifest = dict(schema=1, mods=result)
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf8')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path, help='New SDK_Mods output directory')
    parser.add_argument('--source', type=Path, default=ROOT / 'mods')
    args = parser.parse_args()
    result = build_all(args.source, args.destination)
    print(json.dumps(dict(destination=str(args.destination.resolve()), count=len(result['mods']))))


if __name__ == '__main__':
    main()
