"""Find byte-substring leads and enclosing printable spans; never assign identities."""
import argparse
import hashlib
import json
from pathlib import Path
import pefile

TARGETS = (
    'Unreal Engine 5.4.4', 'GUObjectArray', 'FUObjectArray', 'FNamePool',
    'UObject::ProcessEvent', 'ProcessEvent', 'StaticAllocateObject',
    'StaticFindObject', 'NamePoolData', 'Max UObject count is exceeded',
    'None', '/Script/CoreUObject', '/Script/Engine', 'GameEngine',
    'Object', 'Class', 'Function', 'ByteProperty', '.?AVUObject@@',
    'EasyAntiCheat', 'BattlEye', 'Denuvo', 'WinLicense',
    'UObjectGlobals.cpp', 'UObjectArray.cpp', 'UObjectBase.cpp',
    'UObjectHash.cpp', 'UnrealNames.cpp', 'ScriptCore.cpp',
    'GarbageCollection.cpp', 'NameTypes.h',
)


def printable_span(data, offset, encoding, max_chars=2048):
    width = 2 if encoding == 'utf-16le' else 1

    def printable(at):
        unit = data[at:at + width]
        return (len(unit) == width and 32 <= unit[0] <= 126
                and (width == 1 or unit[1] == 0))

    start = end = offset
    while start >= width and offset - start < max_chars * width and printable(start - width):
        start -= width
    while end < len(data) and end - offset < max_chars * width and printable(end):
        end += width
    return start, data[start:end].decode(encoding), data[end:end + width] == bytes(width)


def scan(path):
    data = path.read_bytes()
    pe = pefile.PE(data=data, fast_load=True)
    results = []
    for target in TARGETS:
        for encoding in ('ascii', 'utf-16le'):
            needle = target.encode(encoding)
            offset = 0
            hits = []
            count = 0
            while (offset := data.find(needle, offset)) >= 0:
                count += 1
                if len(hits) < 32:
                    section = pe.get_section_by_offset(offset)
                    rva = pe.get_rva_from_offset(offset) if section else None
                    start, context, terminated = printable_span(data, offset, encoding)
                    start_rva = pe.get_rva_from_offset(start) if pe.get_section_by_offset(start) else None
                    hits.append({'file_offset': hex(offset),
                                 'rva': hex(rva) if rva is not None else None,
                                 'preferred_va': hex(pe.OPTIONAL_HEADER.ImageBase+rva) if rva is not None else None,
                                 'section': section.Name.rstrip(b'\0').decode() if section else None,
                                 'printable_span': context,
                                 'span_file_offset': hex(start),
                                 'span_preferred_va': hex(pe.OPTIONAL_HEADER.ImageBase + start_rva) if start_rva is not None else None,
                                 'span_null_terminated': terminated})
                offset += len(needle)
            results.append({'text': target, 'encoding': encoding, 'count': count, 'first_hits': hits})
    return {'binary': str(path), 'sha256': hashlib.sha256(data).hexdigest(),
            'status': 'OBSERVED byte substring matches and bounded printable spans only; no global/function identity established',
            'queries': results}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('binary', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = scan(args.binary)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps([{'text': q['text'], 'encoding': q['encoding'], 'count': q['count']}
                      for q in result['queries'] if q['count']], indent=2))
