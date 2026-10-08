"""Read-only target-derived console pointers and vtables; no engine calls."""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import struct
import expedition33

start, rows = expedition33._query(['--limit', '0'])
objects = [r for r in rows if r['event'] == 'object']
base = int(start['module_base'], 16)
kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel.OpenProcess.restype = wintypes.HANDLE
kernel.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
kernel.CloseHandle.argtypes = [wintypes.HANDLE]
process = kernel.OpenProcess(0x1010, False, start['pid'])
assert process
def read(address, size):
    assert 0x10000 <= address < 0x7fffffffffff and 0 < size <= 4096
    buffer = ctypes.create_string_buffer(size)
    received = ctypes.c_size_t()
    assert kernel.ReadProcessMemory(process, address, buffer, size, ctypes.byref(received)) and received.value == size
    return buffer.raw
def u64(address):
    return struct.unpack('<Q', read(address, 8))[0]
def name(identifier):
    pool = base + int(start['name_pool_rva'], 16)
    entry = u64(pool + 0x10 + (identifier >> 16)*8) + (identifier & 65535)*2
    header = struct.unpack('<H', read(entry, 2))[0]
    length, wide = header >> 6, header & 1
    assert 0 < length <= 1023
    return read(entry+2, length*(2 if wide else 1)).decode('utf-16le' if wide else 'ascii')
def validate(row):
    address = int(row['address'], 16)
    assert struct.unpack('<i', read(address + 12, 4))[0] == row['index']
    return address
def select(name):
    matches = [r for r in objects if r['name'] == name]
    assert len(matches) == 1
    return matches[0]
try:
    output = {'pid': start['pid'], 'base': hex(base), 'sha256': start['sha256'], 'objects': {}}
    output['console_state_names'] = {hex(rva): {'raw': hex(u64(base+rva)),
        'name': name(u64(base+rva) & 0xffffffff)} for rva in (0x94dfb50,0x94dfb58)}
    targets = [select('Default__Console'), select('Default__InputSettings'), select('Default__PlayerController')]
    targets += [r for r in objects if r['class_name'] in ('CustomGameViewportClient', 'GameEngine') and not r['name'].startswith('Default__')]
    for row in targets:
        address = validate(row)
        table = u64(address)
        entry = {'identity': row, 'vtable_rva': hex(table-base)}
        if row['class_name'] == 'CustomGameViewportClient':
            entry['viewport_console'] = hex(u64(address + 0x40))
            entry['world'] = hex(u64(address + 0x78))
            entry['game_instance'] = hex(u64(address + 0x80))
        elif row['class_name'] == 'GameEngine':
            entry['console_class'] = hex(u64(address + 0x118))
            entry['viewport'] = hex(u64(address + 0xa80))
        elif row['class_name'] == 'InputSettings':
            pointer, count, capacity = struct.unpack('<Qii', read(address + 0x130, 16))
            assert 0 <= count <= capacity <= 64
            entry['console_keys'] = {'count': count, 'capacity': capacity,
                                    'raw_24byte_elements': read(pointer, count*24).hex() if count else ''}
            entry['console_keys']['names'] = [name(struct.unpack('<I', read(pointer+i*24, 4))[0]) for i in range(count)]
        if row['class_name'] in ('Console', 'CustomGameViewportClient', 'PlayerController'):
            offsets = range(0, 0x400, 8) if row['class_name'] != 'PlayerController' else (0xcf0,0xcf8,0xdd8)
            entry['vtable_entries'] = {hex(offset): hex(u64(table+offset)-base+0x140000000) for offset in offsets}
        assert validate(row) == address
        output['objects'][row['name']] = entry
    (Path(__file__).resolve().parents[1] / 'evidence/console-runtime-pointers.json').write_text(json.dumps(output, indent=2), encoding='utf-8')
    print(json.dumps(output))
finally:
    kernel.CloseHandle(process)
