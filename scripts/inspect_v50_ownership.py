"""Read-only, exact-PDB diagnostic for the pinned v50 candidate after menu shutdown."""
import ctypes as C
from ctypes import wintypes as W
import json
from pathlib import Path
import struct
import uuid
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
DLL = ROOT / 'build/runtime-session-v50-audiocleanupdiagnostics/runtime_session_v50_audiocleanupdiagnostics.dll'
LAYOUT = ROOT / 'evidence/v50-pdb-layout.tsv'
PID = 14156

def main():
    k = C.WinDLL('kernel32', use_last_error=True)
    p = C.WinDLL('psapi', use_last_error=True)
    k.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
    k.OpenProcess.restype = W.HANDLE
    k.CloseHandle.argtypes = [W.HANDLE]
    k.ReadProcessMemory.argtypes = [W.HANDLE, C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(C.c_size_t)]
    p.EnumProcessModulesEx.argtypes = [W.HANDLE, C.POINTER(C.c_void_p), W.DWORD, C.POINTER(W.DWORD), W.DWORD]
    p.GetModuleFileNameExW.argtypes = [W.HANDLE, C.c_void_p, W.LPWSTR, W.DWORD]
    handle = k.OpenProcess(0x410, False, PID)
    if not handle: raise C.WinError(C.get_last_error())
    try:
        def read(at, size):
            if not 0 < size <= 262144: raise ValueError('Read bound')
            buf = C.create_string_buffer(size); got = C.c_size_t()
            if not k.ReadProcessMemory(handle, at, buf, size, C.byref(got)) or got.value != size:
                raise C.WinError(C.get_last_error())
            return buf.raw
        modules = (C.c_void_p * 2048)(); needed = W.DWORD()
        if not p.EnumProcessModulesEx(handle, modules, C.sizeof(modules), C.byref(needed), 3):
            raise C.WinError(C.get_last_error())
        if needed.value > C.sizeof(modules): raise ValueError('Module bound')
        matches=[]
        for address in modules[:needed.value // C.sizeof(C.c_void_p)]:
            name=C.create_unicode_buffer(32768)
            if p.GetModuleFileNameExW(handle,address,name,len(name)) and name.value.lower()==str(DLL).lower():
                matches.append(address)
        if len(matches)!=1: raise ValueError('Exact loaded candidate missing/ambiguous')
        base=matches[0]; disk=DLL.read_bytes(); header=read(base,4096)
        pe=struct.unpack_from('<I',header,60)[0]
        header_size=struct.unpack_from('<I',header,pe+24+60)[0]
        if not 0<header_size<=4096: raise ValueError('PE header bound')
        normalized=bytearray(header[:header_size])
        image_base_offset=pe+24+24
        if struct.unpack_from('<Q',header,image_base_offset)[0] not in (base,struct.unpack_from('<Q',disk,image_base_offset)[0]):
            raise ValueError('Unexpected mapped image base')
        normalized[image_base_offset:image_base_offset+8]=disk[image_base_offset:image_base_offset+8]
        if header[:2]!=b'MZ' or header[pe:pe+4]!=b'PE\0\0' or normalized!=disk[:header_size]:
            raise ValueError('Loaded/disk PE header mismatch at '+repr([(i,header[i],disk[i]) for i in range(header_size) if header[i]!=disk[i]][:32]))
        debug,size=struct.unpack_from('<II',header,pe+24+112+6*8)
        if size>4096 or size%28: raise ValueError('Debug directory bound')
        records=read(base+debug,size); codeview=[]
        for off in range(0,size,28):
            _,_,_,_,kind,extent,rva,_=struct.unpack_from('<IIHHIIII',records,off)
            if kind==2:
                raw=read(base+rva,extent)
                if raw[:4]==b'RSDS': codeview.append((str(uuid.UUID(bytes_le=raw[4:20])),struct.unpack_from('<I',raw,20)[0]))
        lines=LAYOUT.read_text(encoding='utf-8-sig').splitlines()
        pdb=lines[0].split('\t')
        if codeview!=[(pdb[1],int(pdb[2]))]: raise ValueError('Loaded PDB identity mismatch')
        symbols={}; fields={}; lengths={}
        for line in lines:
            row=line.split('\t')
            if row[0]=='SYMBOL': symbols[row[4]]=(int(row[1],16),int(row[2]),int(row[3]))
            elif row[0]=='TYPE': lengths[int(row[1])]=int(row[2])
            elif row[0]=='FIELD': fields.setdefault(int(row[1]),{})[row[4]]=(int(row[2]),int(row[3]))
        def locate(symbol,path=()):
            rva,size,typ=symbols[symbol]; offset=0
            for name in path:
                delta,typ=fields[typ][name];offset+=delta
            return base+rva+offset, lengths.get(typ,size)
        def value(symbol,*path):
            at,size=locate(symbol,path)
            if size not in (1,4,8): raise ValueError((symbol,path,size))
            return int.from_bytes(read(at,size),'little')
        def pool(symbol,*path):
            at,size=locate(symbol,(*path,'entries_','initial_'))
            if size%32 or size>4096: raise ValueError('Initial pool bound')
            raw=read(at,size)
            return dict(initial_slots=size//32,initial_active=sum(bool(struct.unpack_from('<Q',raw,i)[0]) for i in range(0,size,32)),
                capacity=value(symbol,*path,'entries_','capacity_'),peak=value(symbol,*path,'peak_'),closing=value(symbol,*path,'closing_'))
        result=dict(pid=PID,module_base=hex(base),pdb=codeview,
            sequence_state=value('session_sequence','state_'),
            widget_state=value('session_widget_hook','state_'),
            widget_observed=value('session_widget_hook','observed_'),widget_failed=value('session_widget_hook','failed_'),
            widget_private=pool('session_widget_hook','widgets_','leases_'),
            public_leases=pool('session_leases'),
            sound_state=value('session_sound_event','state_'),sound_observed=value('session_sound_event','observed_'),
            sound_failed=value('session_sound_event','failed_'),audio_state=value('session_music_audio','state_'),
            audio_index=value('session_music_audio','index_'),audio_step=value('session_music_audio','step_'),
            audio_cleanup_count=value('session_music_audio','cleanup_','count'),
            audio_explicit_count=value('session_music_audio','explicit_count_'),
            audio_private=pool('session_music_audio','component_leases_'),
            transport={name:value('session_transport::'+name) for name in ('packet','owner_tid','pending_close_reason','completed_closes','last_close_reason')})
        at,_=locate('session_widget_hook',('diagnostics_',))
        result['widget_routes']=dict(zip(('eligible','exact_frames','root_misses','owned_matches','failed'),struct.unpack('<IIIII',read(at,20))))
        result['animation_count']=value('session_widget_hook','widgets_','animations_','count_')
        result['animation_uncertain']=value('session_widget_hook','widgets_','animations_','uncertain_')
        result['journal_state']=value('session_widget_hook','widgets_','journal_','state_')
        result['journal_count']=value('session_widget_hook','widgets_','journal_','count_')
        captured = {}
        if 0 < result['audio_cleanup_count'] <= 64:
            at, extent = locate('session_music_audio', ('cleanup_', 'items'))
            if extent != 1024:
                raise ValueError('Unexpected cleanup identity array extent')
            captured['first_cleanup_target'] = struct.unpack('<iiQ', read(at, 16))
        for label in ('destroy_', 'stop_'):
            at, extent = locate('session_music_audio', (label, 'function'))
            if extent != 16:
                raise ValueError('Unexpected function identity extent')
            captured[label] = struct.unpack('<iiQ', read(at, 16))
        result['captured_audio_identities'] = captured
        from expedition33 import _query
        from expedition33._reader import ReadBatch
        with ReadBatch(PID):
            start, _ = _query(['--catalog-match', str(PID), 'n=BP_jRPG_GI_Custom_C'])
        if start['sha256'] != '218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618':
            raise ValueError('Unverified game build')
        game_base = int(start['module_base'], 16)
        result['cleanup_slot_now'] = {}
        if 'first_cleanup_target' in captured:
            index, serial, address = captured['first_cleanup_target']
            count = int.from_bytes(read(game_base + 0x9361b84, 4), 'little', signed=True)
            chunk_count = int.from_bytes(read(game_base + 0x9361b8c, 4), 'little', signed=True)
            if not 0 <= index < count <= 1048576 or not 0 <= index >> 16 < chunk_count <= 16:
                raise ValueError('Registry bounds rejected')
            chunks = int.from_bytes(read(game_base + 0x9361b70, 8), 'little')
            chunk = int.from_bytes(read(chunks + (index >> 16) * 8, 8), 'little')
            slot = read(chunk + (index & 65535) * 24, 24)
            current_address = struct.unpack_from('<Q', slot)[0]
            current_serial = struct.unpack_from('<i', slot, 16)[0]
            result['cleanup_slot_now'] = dict(index=index, serial=current_serial,
                address=current_address, exact_match=(serial, address) == (current_serial, current_address))
            if (serial, address) == (current_serial, current_address):
                result['cleanup_slot_now']['flags'] = hex(int.from_bytes(read(address + 8, 4), 'little'))
        from expedition33.catalog import capture_selected
        result['fresh_audio_identities'] = {}
        for label, observed in captured.items():
            try:
                fresh = capture_selected(PID, (observed,))
                obj = fresh.by_index[observed[0]]
                if (obj.index, obj.serial, obj.address) != observed:
                    raise ValueError('Identity mismatch')
                result['fresh_audio_identities'][label] = dict(path=fresh.path_name(obj),
                    flags=hex(obj.object_flags), item_flags=hex(obj.item_flags))
            except Exception as error:
                result['fresh_audio_identities'][label] = dict(error=repr(error))
        from expedition33.catalog import capture_matching
        with ReadBatch(PID):
            definitions = capture_matching(PID, names=('Default__AudioComponent', 'SequenceEvent'))
            result['lifecycle_definitions'] = []
            for obj in definitions.objects:
                path = definitions.path_name(obj)
                if not ((obj.name == 'Default__AudioComponent' and obj.class_name == 'AudioComponent') or
                        (obj.name == 'SequenceEvent' and obj.class_name == 'Function' and
                         'LS_Title_PrologueLumiere' in path)):
                    continue
                capture_selected(PID, ((obj.index, obj.serial, obj.address),))
                entry = dict(path=path, identity=[obj.index, obj.serial, obj.address])
                if obj.name == 'Default__AudioComponent':
                    vtable = int.from_bytes(read(obj.address, 8), 'little')
                    if not game_base < vtable < game_base + 0x10000000 - 0x620:
                        raise ValueError('CDO vtable outside bounded game image region')
                    entry.update(vtable_rva=hex(vtable-game_base),
                        stop_rva=hex(int.from_bytes(read(vtable+0x618,8),'little')-game_base),
                        destroy_rva=hex(int.from_bytes(read(vtable+0x458,8),'little')-game_base))
                else:
                    entry.update(event_graph_pointer=hex(int.from_bytes(read(obj.address+0xc8,8),'little')),
                                 event_graph_entry=int.from_bytes(read(obj.address+0xd0,4),'little',signed=True))
                result['lifecycle_definitions'].append(entry)
        out=ROOT/'evidence/v50-native-audio-identity.json'
        out.write_text(json.dumps(result,indent=2),encoding='utf8')
        print(json.dumps(result,indent=2))
    finally: k.CloseHandle(handle)

if __name__=='__main__': main()

