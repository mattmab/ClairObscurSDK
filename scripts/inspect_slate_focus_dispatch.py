"""Read target-derived Slate focus dispatch pointers; never call them.

Offsets come from widget-focus-thunks/slate-focus-query Ghidra artifacts.
Pointer stability checks are observations, not shared-reference ownership.
"""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import struct
import time

from expedition33 import _query
from expedition33.catalog import capture


def _observe_once():
    start, _ = _query(['--limit', '1'])
    assert start['sha256'] == '218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618'
    base = int(start['module_base'], 16)
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
        buf, got = ctypes.create_string_buffer(size), ctypes.c_size_t()
        if not kernel.ReadProcessMemory(handle, address, buf, size, ctypes.byref(got)) or got.value != size:
            raise RuntimeError('Slate observation unavailable')
        return buf.raw
    def u64(address):
        return struct.unpack('<Q', read(address, 8))[0]
    def array(address, limit):
        header = read(address, 16)
        pointer, count, capacity = struct.unpack('<Qii', header)
        assert 0 <= count <= capacity <= limit, f'Array header at {address:#x}: count={count}, capacity={capacity}, limit={limit}'
        return header, pointer, count
    def rva(address):
        assert base <= address < base + 166776832
        return hex(address-base)
    result = dict(pid=start['pid'], sha256=start['sha256'], read_only=True)
    try:
        app = u64(base+0x938d218)
        app_base = u64(base+0x93652a0)
        mapping = u64(app+0x690)
        result.update(application=hex(app), application_base=hex(app_base),
                      application_vtable=rva(u64(app)), base_vtable=rva(u64(app_base)),
                      user_mapping_vtable=rva(u64(mapping)),
                      user_focus_query=rva(u64(u64(app_base)+0x190)),
                      viewport_focus_path_dispatch=rva(u64(u64(app)+0x160)),
                      keyboard_user_query=rva(u64(u64(mapping)+8)),
                      controller_user_query=rva(u64(u64(mapping)+0x38)))
        # 15ed2d0 indexes 16-byte user references at application+2f8.
        # 163dc80 promotes the last weak widget in user+70's focus path.
        header, users, count = array(app+0x2f8, 64)
        assert count <= 16, 'Diagnostic only inspects at most sixteen Slate users'
        result['users'] = []
        for index in range(count):
            reference = read(users+index*16, 16)
            user, owner = struct.unpack('<QQ', reference)
            row = dict(index=index, address=hex(user), owner=hex(owner))
            if user:
                assert owner and struct.unpack('<i', read(owner+8, 4))[0] > 0
                path_header, path, path_count = array(user+0x70, 128)
                row['focus_path_count'] = path_count
                if path_count:
                    weak = read(path+(path_count-1)*16, 16)
                    widget, control = struct.unpack('<QQ', weak)
                    row.update(last_widget=hex(widget), last_control=hex(control))
                    if control:
                        refs = read(control+8, 8)
                        strong_count, weak_count = struct.unpack('<ii', refs)
                        row.update(strong_count=strong_count, weak_count=weak_count)
                        if strong_count > 0 and widget:
                            row['widget_vtable'] = rva(u64(widget))
                        assert refs == read(control+8, 8)
                    assert weak == read(path+(path_count-1)*16, 16)
                assert path_header == read(user+0x70, 16)
            assert reference == read(users+index*16, 16)
            result['users'].append(row)
        assert header == read(app+0x2f8, 16)
        catalog = capture()
        assert catalog.pid == start['pid']
        engines = [o for o in catalog.select('GameEngine') if not o.object_flags & 0x10]
        assert len(engines) == 1
        engine = engines[0]
        assert struct.unpack('<i', read(engine.address+12, 4))[0] == engine.index
        assert u64(engine.address+16) == catalog.by_index[engine.class_index].address
        viewport_ref = read(engine.address+0x10d0, 16)
        viewport, viewport_owner = struct.unpack('<QQ', viewport_ref)
        result['game_viewport'] = dict(engine_path=catalog.path_name(engine),
            widget=hex(viewport), owner=hex(viewport_owner), vtable=rva(u64(viewport)))
        control_vtable = u64(viewport_owner)
        result['viewport_reference_type'] = dict(vtable=rva(control_vtable),
            destroy_object=rva(u64(control_vtable)), destroy_controller=rva(u64(control_vtable+8)))
        registered_viewport = read(app+0x398, 16)
        result['registered_viewport_matches_game_viewport'] = registered_viewport == viewport_ref
        assert registered_viewport == read(app+0x398, 16)
        for row in result['users']:
            row['matches_game_viewport'] = (row.get('last_widget') == hex(viewport)
                                           and row.get('last_control') == hex(viewport_owner))
        assert viewport_ref == read(engine.address+0x10d0, 16)
        assert u64(base+0x938d218) == app and u64(base+0x93652a0) == app_base
        assert u64(app+0x690) == mapping
    finally:
        kernel.CloseHandle(handle)
    return result


def observe():
    # Refcounts can change while the engine processes a console transition.
    # Retry the read-only snapshot; never retry an engine mutation here.
    for attempt in range(3):
        try:
            result = _observe_once()
            result['observation_attempts'] = attempt + 1
            return result
        except AssertionError:
            if attempt == 2:
                raise
            time.sleep(.05)


def main():
    result = observe()
    (Path(__file__).resolve().parents[1]/'evidence/slate-focus-dispatch.json').write_text(
        json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
