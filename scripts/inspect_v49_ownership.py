"""Read-only, exact-PDB diagnostic for the pinned v49 candidate after failure."""
import ctypes as C
from ctypes import wintypes as W
import json
from pathlib import Path
import struct
import uuid

ROOT = Path(__file__).resolve().parents[1]
DLL = ROOT / 'build/runtime-session-v49-animationdrain/runtime_session_v49_animationdrain.dll'
LAYOUT = ROOT / 'evidence/animation-v49-pdb-layout.tsv'
PID = 9616

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
        out=ROOT/'evidence/animation-v49-native-after-failure.json'
        out.write_text(json.dumps(result,indent=2),encoding='utf8')
        print(json.dumps(result,indent=2))
    finally: k.CloseHandle(handle)

if __name__=='__main__': main()
