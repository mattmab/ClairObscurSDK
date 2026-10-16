"""Package the optional World Builder independently of the base SDK."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))

from package_mods import build_all

ROOT = Path(__file__).resolve().parents[1]


def build(destination):
    destination = Path(destination).resolve()
    manifest = build_all(ROOT / 'mods', destination / 'SDK_Mods', include={'E33WorldBuilder'})
    archive = destination / 'E33WorldBuilder-0.30.1.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as out:
        out.write(destination / 'SDK_Mods/E33WorldBuilder.sdkmod', 'SDK_Mods/E33WorldBuilder.sdkmod')
        out.write(ROOT / 'mods/E33WorldBuilder/README.txt', 'README-WorldBuilder.txt')
        out.write(ROOT / 'LICENSE', 'LICENSE')
    result = dict(archive=str(archive), sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                  requires_sdk='0.1.0-rc12', mods=manifest['mods'])
    (destination / 'artifact.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    print(json.dumps(build(parser.parse_args().destination)))
