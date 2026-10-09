"""Read-only corroboration of target-derived GC holder layout; no engine calls.

Does not pin objects, acquire the target critical section, or claim GC atomicity.
All native offsets below come from the recorded Ghidra ownership paths.
"""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import struct

from expedition33 import _query


def main():
    start, rows = _query(['--limit', '0'])
    assert start['sha256'] == '218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618'
    base = int(start['module_base'], 16)
    observed = {int(row['address'], 16): row for row in rows if row['event'] == 'object'}
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                       ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1010, False, start['pid'])
    if not handle: raise ctypes.WinError(ctypes.get_last_error())
    def read(address, size):
        if not 0x10000 <= address < 0x7fffffffffff or not 0 < size <= 65536:
            raise ValueError('Read outside probe bounds')
        buffer, received = ctypes.create_string_buffer(size), ctypes.c_size_t()
        if not kernel.ReadProcessMemory(handle, address, buffer, size, ctypes.byref(received)) or received.value != size:
            raise RuntimeError('Native holder changed or memory read failed')
        return buffer.raw
    def u64(address): return struct.unpack('<Q', read(address, 8))[0]
    def identity(address):
        row = observed.get(address)
        if row is None: raise RuntimeError('Referenced UObject absent from current enumeration')
        index = struct.unpack('<i', read(address + 12, 4))[0]
        count = struct.unpack('<i', read(base + 0x9361b84, 4))[0]
        if index != row['index'] or not 0 <= index < count: raise RuntimeError('Object index changed')
        chunks = u64(base + 0x9361b70)
        slot = u64(chunks + (index >> 16) * 8) + (index & 65535) * 24
        raw = read(slot, 24)
        if struct.unpack_from('<Q', raw)[0] != address or struct.unpack_from('<i', raw, 16)[0] != row['serial']:
            raise RuntimeError('Object registry identity changed')
        return {'index': index, 'serial': row['serial'], 'name': row['name'], 'class': row['class_name']}
    try:
        referencer = u64(base + 0x9346f60)
        owner = identity(referencer)
        assert owner['class'] == 'GCObjectReferencer'
        state = u64(referencer + 0x28)
        collections = []
        for offset, name in ((0x28, 'normal'), (0x38, 'conditional')):
            header = read(state + offset, 16)
            pointer, count, capacity = struct.unpack('<Qii', header)
            assert 0 <= count <= capacity <= 65536
            def members():
                return b''.join(read(pointer + at, min(65536, count * 8 - at))
                                for at in range(0, count * 8, 65536))
            before = members()
            widgets = []
            for (holder,) in struct.iter_unpack('<Q', before):
                if u64(holder) != base + 0x739f468:
                    continue
                raw = read(holder, 24)
                widget = struct.unpack_from('<Q', raw, 16)[0]
                item = {'registered': bool(raw[9]), 'conditional': bool(raw[8]),
                        'holder_address': hex(holder), 'widget': identity(widget) if widget else None}
                if raw != read(holder, 24): raise RuntimeError('Slate holder changed during probe')
                assert item['registered'] and item['conditional'] == (offset == 0x38)
                widgets.append(item)
            if header != read(state + offset, 16) or before != members():
                raise RuntimeError('GC registration list changed during probe')
            collections.append({'name': name, 'count': count, 'capacity': capacity, 'slate_widgets': widgets})
        if referencer != u64(base + 0x9346f60) or state != u64(referencer + 0x28):
            raise RuntimeError('GC referencer changed')
        identity(referencer)
        result = {'pid': start['pid'], 'sha256': start['sha256'], 'referencer': owner,
                  'collections': collections, 'read_only': True, 'gc_atomic': False,
                  'sdk_retention_implemented': False}
        path = Path(__file__).resolve().parents[1] / 'evidence/gc-owners-live.json'
        path.write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps({'pid': start['pid'], 'referencer': owner,
                          'collections': [{'name': row['name'], 'count': row['count'],
                                           'slate_widgets': len(row['slate_widgets'])} for row in collections]}))
    finally:
        kernel.CloseHandle(handle)


if __name__ == '__main__': main()
