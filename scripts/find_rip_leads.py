"""Find candidate x64 RIP-relative LEA encodings; Ghidra must validate boundaries.

This is a bounded lead finder, not a disassembler or runtime signature resolver.
Executable-section data can match these bytes without being an instruction.
"""
import argparse
from bisect import bisect_right
import hashlib
import json
from pathlib import Path
import re
import struct

import pefile


def scan(binary, targets):
    data = binary.read_bytes()
    pe = pefile.PE(data=data, fast_load=True)
    base = pe.OPTIONAL_HEADER.ImageBase
    if pe.FILE_HEADER.Machine != 0x8664:
        raise ValueError('Only x64 PE images are supported')
    exception = pe.OPTIONAL_HEADER.DATA_DIRECTORY[3]
    table = pe.get_data(exception.VirtualAddress, exception.Size)
    ranges = sorted((start, end, unwind) for start, end, unwind in
                    struct.iter_unpack('<III', table) if start < end)
    starts = [row[0] for row in ranges]
    candidates = []
    # REX.W + LEA + ModRM with mod=00 and r/m=101, then disp32.
    pattern = re.compile(rb'[\x48-\x4f]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]')
    for section in pe.sections:
        if not section.Characteristics & 0x20000000:
            continue
        raw = section.get_data()
        for match in pattern.finditer(raw):
            at = match.start()
            if at + 7 > len(raw):
                continue
            rva = section.VirtualAddress + at
            target = base + rva + 7 + struct.unpack_from('<i', raw, at + 3)[0]
            if target not in targets:
                continue
            index = bisect_right(starts, rva) - 1
            unwind_range = None
            if index >= 0 and ranges[index][0] <= rva < ranges[index][1]:
                start, end, unwind = ranges[index]
                unwind_range = {'start': hex(base + start), 'end_exclusive': hex(base + end),
                                'unwind_info': hex(base + unwind)}
            candidates.append({'candidate_instruction_va': hex(base + rva),
                               'candidate_rva': hex(rva), 'target_va': hex(target),
                               'bytes': raw[at:at + 7].hex(),
                               'pe_exception_range': unwind_range})
    return {'binary': str(binary), 'sha256': hashlib.sha256(data).hexdigest(),
            'status': 'HYPOTHESIS: raw LEA encoding candidates; verify instruction boundaries and behavior in Ghidra',
            'targets': [hex(target) for target in sorted(targets)], 'candidates': candidates}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    parser.add_argument('--target', action='append', required=True, type=lambda x: int(x, 0))
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = scan(args.binary, set(args.target))
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result['candidates'], indent=2))
