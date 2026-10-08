"""Read-only PE headers and bounded build-string evidence; no target execution."""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path


def inspect(path):
    data = path.read_bytes()
    if data[:2] != b'MZ':
        raise ValueError('Not an MZ image')
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    if data[pe:pe+4] != b'PE\0\0':
        raise ValueError('Not a PE image')
    machine, count, timestamp, _, _, optsize, flags = struct.unpack_from('<HHIIIHH', data, pe+4)
    opt = pe+24
    magic = struct.unpack_from('<H', data, opt)[0]
    if magic != 0x20b:
        raise ValueError('Expected PE32+')
    base = struct.unpack_from('<Q', data, opt+24)[0]
    sections = []
    for i in range(count):
        offset = opt+optsize+i*40
        name, vsize, rva, rawsize, raw = struct.unpack_from('<8sIIII', data, offset)
        sections.append(dict(name=name.rstrip(b'\0').decode('ascii', 'replace'),
                             virtual_size=vsize, rva=hex(rva), raw_size=rawsize, raw_offset=raw))
    patterns = [rb'\+\+UE5[^\x00\r\n]{0,160}', rb'Unreal Engine[^\x00\r\n]{0,100}',
                rb'[45]\.[0-9]+\.[0-9]+-[0-9]+[^\x00\r\n]{0,100}',
                rb'[^\x00\r\n]{0,80}\.pdb', rb'EasyAntiCheat', rb'BattlEye', rb'Denuvo', rb'WinLicense']
    strings = []
    for encoding, view, stride, alignment in [('ascii', data, 1, 0),
                                               ('utf-16le', data[::2], 2, 0),
                                               ('utf-16le', data[1::2], 2, 1)]:
        for pattern in patterns:
            for m in re.finditer(pattern, view):
                start, end = m.start()*stride+alignment, m.end()*stride+alignment
                if stride == 2 and any(data[start+1:end:2]):
                    continue  # Every high byte must be zero for these ASCII-range UTF-16 leads.
                strings.append(dict(encoding=encoding, file_offset=hex(start),
                                    text=m.group().decode('ascii','replace')))
                if len(strings) > 150:
                    break
    return dict(path=str(path), sha256=hashlib.sha256(data).hexdigest(), size=len(data),
                machine=hex(machine), timestamp=timestamp, image_base=hex(base),
                entry_rva=hex(struct.unpack_from('<I', data, opt+16)[0]),
                image_size=struct.unpack_from('<I', data, opt+56)[0],
                clr_directory=struct.unpack_from('<II', data, opt+112+14*8), sections=sections,
                strings=strings, note='String matches are leads, not proof of active protection or engine layout.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('binary', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.write_text(json.dumps(inspect(args.binary), indent=2), encoding='utf-8')
