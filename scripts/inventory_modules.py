"""Inventory native/managed module boundaries without executing target code."""
import argparse
import json
from pathlib import Path
import pefile


def inventory(root):
    records = []
    for path in sorted(list(root.rglob('*.exe')) + list(root.rglob('*.dll'))):
        with pefile.PE(str(path), fast_load=True) as pe:
            pe.parse_data_directories(directories=[1, 13])
            records.append(dict(
                path=str(path.relative_to(root)), machine=hex(pe.FILE_HEADER.Machine),
                clr=bool(pe.OPTIONAL_HEADER.DATA_DIRECTORY[14].VirtualAddress),
                sections=[s.Name.rstrip(b'\0').decode(errors='replace') for s in pe.sections],
                imports=[x.dll.decode(errors='replace') for x in getattr(pe, 'DIRECTORY_ENTRY_IMPORT', [])],
                delay_imports=[x.dll.decode(errors='replace') for x in getattr(pe, 'DIRECTORY_ENTRY_DELAY_IMPORT', [])],
            ))
    return records


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    records = inventory(args.root)
    args.output.write_text(json.dumps(records, indent=2), encoding='utf-8')
    print('Parsed modules:', len(records))
    print('Managed modules:', [r['path'] for r in records if r['clr']])
    for record in records:
        if record['path'].endswith('Shipping.exe') or record['path'] == 'Expedition33_Steam.exe':
            print(json.dumps(record, indent=2))
