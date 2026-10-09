"""Read target-derived class/initializer pointers; never construct a widget."""
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
    objects = [row for row in rows if row['event'] == 'object']
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                       ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1010, False, start['pid'])
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())

    def read(address, size):
        assert 0x10000 <= address < 0x7fffffffffff and 0 < size <= 4096
        buffer, received = ctypes.create_string_buffer(size), ctypes.c_size_t()
        if not kernel.ReadProcessMemory(handle, address, buffer, size, ctypes.byref(received)) or received.value != size:
            raise RuntimeError('Widget probe read failed')
        return buffer.raw

    def u64(address):
        return struct.unpack('<Q', read(address, 8))[0]

    def identity(row):
        address = int(row['address'], 16)
        index = struct.unpack('<i', read(address + 12, 4))[0]
        count = struct.unpack('<i', read(base + 0x9361b84, 4))[0]
        assert index == row['index'] and 0 <= index < count
        chunks = u64(base + 0x9361b70)
        slot = u64(chunks + (index >> 16) * 8) + (index & 65535) * 24
        raw = read(slot, 24)
        assert struct.unpack_from('<Q', raw)[0] == address
        assert struct.unpack_from('<i', raw, 16)[0] == row['serial']
        return address

    def one(name, class_name):
        matches = [row for row in objects if row['name'] == name and row['class_name'] == class_name]
        assert len(matches) == 1, (name, len(matches))
        return matches[0]

    def image_pointer(address):
        assert base <= address < base + 166776832
        return {'rva': hex(address-base), 'ghidra': hex(0x140000000+address-base)}

    try:
        cls, cdo = one('UserWidget', 'Class'), one('Default__UserWidget', 'UserWidget')
        class_address, cdo_address = identity(cls), identity(cdo)
        # Constructor at class+b0 is called by target1413bf660. Initializer
        # virtual+318 is called by143119950 after construction/player context.
        constructor = u64(class_address + 0xb0)
        flags = struct.unpack('<I', read(class_address + 0xd4, 4))[0]
        vtable = u64(cdo_address)
        initializer = u64(vtable + 0x318)
        callbacks = {hex(offset): image_pointer(u64(vtable + offset))
                     for offset in (0x320, 0x350)}
        assert u64(cdo_address + 0x10) == class_address
        identity(cls); identity(cdo)
        assert constructor == u64(class_address + 0xb0)
        assert initializer == u64(u64(cdo_address) + 0x318)
        result = {'pid': start['pid'], 'sha256': start['sha256'],
                  'class': cls, 'cdo': cdo, 'class_flags_raw': hex(flags),
                  'constructor': image_pointer(constructor),
                  'initializer': image_pointer(initializer),
                  'initializer_callbacks': callbacks,
                  'read_only': True, 'gc_atomic': False, 'creation_tested': False}
        (Path(__file__).resolve().parents[1]/'evidence/widget-initialization-live.json').write_text(
            json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps(result, indent=2))
    finally:
        kernel.CloseHandle(handle)


if __name__ == '__main__':
    main()
