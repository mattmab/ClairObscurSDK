"""Read live UMG button event metadata; no hooks, bindings or callbacks."""
import json
from pathlib import Path
import sys
import ctypes
from ctypes import wintypes
import struct
import runpy

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from expedition33.catalog import capture
from expedition33 import _query
from expedition33.reflection import describe


def main():
    catalog=capture()
    cls=catalog.by_index[catalog.find_class('Button').index]
    functions=[o for o in catalog.objects if o.outer_index==cls.index and o.class_name=='Function']
    schema=describe(catalog,[cls,*functions])
    properties=[dict(p) for p in schema[cls.index].properties if p['owner_index']==cls.index]
    signatures={p['signature_function_index'] for p in properties if 'signature_function_index' in p}
    signatures=describe(catalog,[catalog.by_index[index] for index in sorted(signatures)])
    def row(descriptor):
        return dict(path=catalog.path_name(descriptor.object),index=descriptor.object.index,
                    serial=descriptor.object.serial,owners=[dict(o) for o in descriptor.owners],
                    properties=[dict(p) for p in descriptor.properties],
                    function=dict(descriptor.function) if descriptor.function else None)
    result=dict(pid=catalog.pid,read_only=True,button_properties=properties,
                functions=[row(schema[o.index]) for o in functions],
                signatures=[row(d) for d in signatures.values()])
    start,_=_query(['--limit','1'])
    assert start['pid']==catalog.pid and start['sha256']=='218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618'
    base=int(start['module_base'],16)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.ReadProcessMemory.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.OpenProcess(0x1010,False,catalog.pid)
    if not handle: raise ctypes.WinError(ctypes.get_last_error())
    def read(at,size):
        data=ctypes.create_string_buffer(size); got=ctypes.c_size_t()
        if not kernel.ReadProcessMemory(handle,at,data,size,ctypes.byref(got)) or got.value!=size:
            raise RuntimeError('Button pointer observation failed')
        return data.raw
    def pointer(at): return struct.unpack('<Q',read(at,8))[0]
    def rva(value):
        assert base<=value<base+166776832
        return hex(value-base)
    try:
        cdos=[o for o in catalog.objects if o.class_index==cls.index and o.name=='Default__Button']
        assert len(cdos)==1
        cdo=cdos[0]
        assert struct.unpack('<i',read(cls.address+12,4))[0]==cls.index
        assert struct.unpack('<i',read(cdo.address+12,4))[0]==cdo.index
        assert pointer(cdo.address+16)==cls.address
        constructor,table=pointer(cls.address+0xb0),pointer(cdo.address)
        result['native_pointers']=dict(constructor_rva=rva(constructor),cdo_vtable_rva=rva(table))
        # Offsets now derived from target RebuildWidget307c280 and SButton
        # construction16cc9a0, not stock headers. Observe at most eight live
        # exact-base Button instances; no delegate binding/callback invocation.
        observed=[]
        for button in catalog.objects:
            if button.class_index!=cls.index or button.object_flags & 0x10: continue
            slate,control=struct.unpack('<QQ',read(button.address+0x5f8,16))
            if not slate or not control: continue
            delegate,units,trailing_word=struct.unpack('<Qii',read(slate+0x2d8,16))
            if not delegate or units!=3: continue
            raw=read(delegate,48)
            vt=struct.unpack_from('<Q',raw)[0]
            weak=struct.unpack_from('<ii',raw,0x18)
            entry=struct.unpack_from('<Q',raw,0x20)[0]
            adjustment=struct.unpack_from('<i',raw,0x28)[0]
            assert vt==base+0x7382098 and entry==base+0x3089290 and adjustment==0
            assert weak==(button.index,button.serial)
            assert pointer(button.address+16)==cls.address
            assert read(button.address+0x5f8,16)==struct.pack('<QQ',slate,control)
            assert read(delegate,48)==raw
            observed.append(dict(path=catalog.path_name(button),index=button.index,serial=button.serial,
                                 slate=hex(slate),slate_vtable_rva=rva(pointer(slate)),
                                 slate_controller=hex(control),controller_vtable_rva=rva(pointer(control)),
                                 delegate=hex(delegate),delegate_vtable_rva=rva(vt),units=units,
                                 trailing_word_observation=trailing_word,callback_rva=rva(entry),adjustment=adjustment))
            if len(observed)==8: break
        result['constructed_button_observations']=observed
        assert pointer(cls.address+0xb0)==constructor and pointer(cdo.address)==table
        result['sha256']=start['sha256']
    finally: kernel.CloseHandle(handle)
    (ROOT/'evidence/button-events-live.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    return result


if __name__=='__main__':
    if sys.argv[1:]==['--owned-specimen']:
        from expedition33 import sdk
        def inspect_owned(scope,widget,child,player):
            result=main()
            matches=[row for row in result['constructed_button_observations']
                     if row['index']==child.index and row['serial']==child.serial]
            assert len(matches)==1, 'Owned button delegate was not corroborated'
            return {'owned_button_delegate_verified':True}
        with sdk.Session(menu_ownership=True) as session:
            runpy.run_path(str(ROOT/'scripts/verify_live_widget_visible.py'))['run'](
                session,hold_seconds=0,on_display=inspect_owned,
                evidence_name='button-event-specimen-live.json')
    else: main()
