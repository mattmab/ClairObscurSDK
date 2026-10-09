"""Bounded read-only corroboration of CommonUI Ghidra paths for this build.

No engine calls, writes, pins, or atomic-GC snapshot are claimed.
"""
import ctypes
from ctypes import wintypes
from dataclasses import asdict
import json
from pathlib import Path
import struct

from expedition33 import _query
from expedition33.catalog import capture


def main():
    catalog = capture()
    start, _ = _query(['--limit', '1'])
    assert start['pid'] == catalog.pid
    assert start['sha256'] == '218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618'
    base = int(start['module_base'], 16)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                       ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1010, False, catalog.pid)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    def read(address, size):
        assert 0x10000 <= address < 0x7fffffffffff and 0 < size <= 4096
        buffer, received = ctypes.create_string_buffer(size), ctypes.c_size_t()
        if not kernel.ReadProcessMemory(handle, address, buffer, size, ctypes.byref(received)) or received.value != size:
            raise RuntimeError('Native state unavailable')
        return buffer.raw
    def u64(address):
        return struct.unpack('<Q', read(address, 8))[0]
    def identity(obj):
        assert struct.unpack('<i', read(obj.address + 12, 4))[0] == obj.index
        chunks = u64(base + 0x9361b70)
        count = struct.unpack('<i', read(base + 0x9361b84, 4))[0]
        assert 0 <= obj.index < count
        slot = u64(chunks + (obj.index >> 16) * 8) + (obj.index & 65535) * 24
        raw = read(slot, 24)
        assert struct.unpack_from('<Q', raw)[0] == obj.address
        assert struct.unpack_from('<i', raw, 16)[0] == obj.serial
        assert u64(obj.address + 16) == catalog.by_index[obj.class_index].address
    result = dict(pid=catalog.pid, sha256=start['sha256'], read_only=True, objects=[])
    try:
        candidates = [o for o in catalog.select('CommonActivatableWidget')
                      if o.name == 'Default__CommonActivatableWidget' or
                      (catalog.path_name(o).startswith('/Engine/Transient.') and
                       (o.name.startswith('WBP_MM_MainMenu_C_') or o.name == 'TitleScreen'))]
        candidates += [o for o in catalog.select('CommonUIActionRouterBase') if not o.object_flags & 0x10]
        assert len(candidates) <= 8
        for obj in candidates:
            identity(obj)
            vtable = u64(obj.address)
            row = dict(object=asdict(obj), path=catalog.path_name(obj), vtable_rva=hex(vtable-base))
            if obj.class_name == 'CommonUIActionRouterBase':
                state = read(obj.address + 0x30, 8)
                root = read(obj.address + 0x88, 16)
                row.update(config_bytes=state.hex(), optional_engaged=state[7],
                           mode_byte=state[3], capture_byte=state[4], hide_cursor_byte=state[6],
                           active_root_bytes=root.hex())
                assert state == read(obj.address + 0x30, 8) and root == read(obj.address + 0x88, 16)
            else:
                row['virtuals'] = {hex(offset): hex(u64(vtable + offset)-base)
                                   for offset in (0x4c0, 0x4c8, 0x4d0, 0x4e0, 0x4e8)}
                row['active'] = read(obj.address + 0x368, 1)[0]
            identity(obj)
            assert u64(obj.address) == vtable
            result['objects'].append(row)
    finally:
        kernel.CloseHandle(handle)
    output = Path(__file__).resolve().parents[1] / 'evidence/commonui-native-state.json'
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    for row in result['objects']:
        print(row['object']['name'], {k:v for k,v in row.items() if k not in ('object','path')})


if __name__ == '__main__':
    main()
