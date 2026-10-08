"""Read-only relationship evidence; snapshots do not pin objects against GC."""
import ctypes
from ctypes import wintypes
from dataclasses import asdict
import json
from pathlib import Path
import struct

import expedition33


def main():
    metadata = {n: expedition33.reflect_class(n) for n in
                ('GameInstance', 'LocalPlayer', 'PlayerController', 'Actor')}
    start, rows = expedition33._query(['--limit', '0'])
    objects = {int(r['address'], 16): r for r in rows if r['event'] == 'object'}
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p,
                                        ctypes.c_void_p, ctypes.c_size_t,
                                        ctypes.POINTER(ctypes.c_size_t)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    process = kernel.OpenProcess(0x1010, False, start['pid'])
    if not process:
        raise ctypes.WinError(ctypes.get_last_error())

    def read(address, size):
        if not 0x10000 <= address < 0x7fffffffffff or not 0 < size <= 4096:
            raise ValueError('Invalid bounded read')
        buffer = ctypes.create_string_buffer(size)
        received = ctypes.c_size_t()
        if not kernel.ReadProcessMemory(process, address, buffer, size,
                                        ctypes.byref(received)) or received.value != size:
            raise ctypes.WinError(ctypes.get_last_error())
        return buffer.raw

    def identity(address):
        row = objects[address]
        if struct.unpack('<i', read(address + 12, 4))[0] != row['index']:
            raise ValueError('Object index changed')
        return row

    def offset(class_name, property_name):
        matches = [p.offset for p in metadata[class_name].properties
                   if p.name == property_name]
        if len(matches) != 1:
            raise ValueError('Ambiguous reflected property')
        return matches[0]

    links = []

    def link(source, class_name, property_name):
        before = read(source, 40)
        identity(source)
        pointer = struct.unpack('<Q', read(source + offset(class_name, property_name), 8))[0]
        target = identity(pointer) if pointer else None
        if read(source, 40) != before:
            raise ValueError('Source identity changed')
        links.append({'source': objects[source], 'property': property_name,
                      'offset': offset(class_name, property_name), 'target': target})
        return pointer

    try:
        players = [a for a, r in objects.items() if r['class_name'] == 'LocalPlayer'
                   and not r['name'].startswith('Default__')]
        for player in players:
            viewport = link(player, 'LocalPlayer', 'ViewportClient')
            controller = link(player, 'LocalPlayer', 'PlayerController')
            if controller:
                if link(controller, 'PlayerController', 'Player') != player:
                    raise ValueError('Player/controller backlink mismatch')
                component = link(controller, 'Actor', 'RootComponent')
                if component:
                    outer = struct.unpack('<Q', read(component + 32, 8))[0]
                    links.append({'source': identity(component), 'property': 'UObject.Outer',
                                  'offset': 32, 'target': identity(outer)})
            if viewport:
                # Viewport GameInstance +0x80 was independently verified by the console probe.
                instance = struct.unpack('<Q', read(viewport + 0x80, 8))[0]
                before = read(instance, 40)
                identity(instance)
                header = read(instance + offset('GameInstance', 'LocalPlayers'), 16)
                pointer, count, capacity = struct.unpack('<Qii', header)
                if not 0 <= count <= capacity <= 64:
                    raise ValueError('Invalid bounded LocalPlayers array')
                members = list(struct.unpack('<' + 'Q' * count, read(pointer, count * 8))) if count else []
                if player not in members:
                    raise ValueError('LocalPlayer missing from GameInstance')
                if read(instance, 40) != before or read(instance + offset('GameInstance', 'LocalPlayers'), 16) != header:
                    raise ValueError('GameInstance or array changed')
                links.append({'source': objects[instance], 'property': 'LocalPlayers',
                              'offset': offset('GameInstance', 'LocalPlayers'),
                              'count': count, 'capacity': capacity,
                              'targets': [identity(a) for a in members]})
        if not players:
            raise ValueError('No live LocalPlayer observed')
        result = {'pid': start['pid'], 'sha256': start['sha256'],
                  'limitation': 'External observations; identity checks are not GC pinning or an atomic snapshot.',
                  'metadata': {n: asdict(m) for n, m in metadata.items()}, 'links': links}
        destination = Path(__file__).resolve().parents[1] / 'evidence/runtime-relationships.json'
        destination.write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps({'pid': start['pid'], 'local_players': len(players), 'links': links}))
    finally:
        kernel.CloseHandle(process)


if __name__ == '__main__':
    main()
