"""Prepare the pinned official CPython runtime; no system installation changes."""
import hashlib
from io import BytesIO
from pathlib import Path
import urllib.request
import zipfile

URL = 'https://www.python.org/ftp/python/3.13.15/python-3.13.15-embed-amd64.zip'
# Published at https://www.python.org/downloads/release/python-31315/
SHA256 = 'd1f04d990aee1253d8569e8e5104e30fa9f5fa830899f14843448872d936a2cf'


def main():
    target = Path(__file__).resolve().parents[1] / 'runtime'
    if target.exists():
        raise SystemExit('runtime already exists; refusing to overwrite a possibly running interpreter')
    with urllib.request.urlopen(URL, timeout=60) as response:
        data = response.read(20_000_001)
    if len(data) > 20_000_000 or hashlib.sha256(data).hexdigest() != SHA256:
        raise SystemExit('Official CPython archive checksum mismatch')
    with zipfile.ZipFile(BytesIO(data)) as archive:
        for item in archive.infolist():
            if not (target / item.filename).resolve().is_relative_to(target):
                raise SystemExit('Invalid archive path')
        target.mkdir()
        archive.extractall(target)
    print(f'Prepared CPython 3.13.15 at {target}; archive SHA256 {SHA256}')


if __name__ == '__main__':
    main()
