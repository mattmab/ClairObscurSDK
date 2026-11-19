// Compile the actual query/gate implementation without running its entrypoint.
#define main research_probe_fixture_entry
#include "../../native/research_probe.cpp"
#undef main
#include <cassert>

struct FixtureChecks {
    unsigned failure=99,calls=0;
    bool next(){return calls++!=failure;}
    bool process_alive(){return next();}
    bool image_identity(){return next();}
    bool module_mapping(){return next();}
    bool image_headers(){return next();}
};

int main(){
    FixtureChecks good;
    validate_reader_session_request(good);assert(good.calls==4);
    good.calls=0;validate_reader_session_request(good);assert(good.calls==4);
    for(unsigned stage=0;stage<4;++stage){
        FixtureChecks bad{stage,0};bool rejected=false;
        try{validate_reader_session_request(bad);}catch(const std::runtime_error&){rejected=true;}
        assert(rejected&&bad.calls==stage+1);
    }
    BY_HANDLE_FILE_INFORMATION expected{};
    expected.dwVolumeSerialNumber=2;expected.nFileIndexHigh=3;expected.nFileIndexLow=4;
    expected.nFileSizeHigh=5;expected.nFileSizeLow=6;
    assert(reader_image_identity_equal(expected,expected));
    for(unsigned field=0;field<5;++field){
        auto changed=expected;
        DWORD* values[]={&changed.dwVolumeSerialNumber,&changed.nFileIndexHigh,&changed.nFileIndexLow,
            &changed.nFileSizeHigh,&changed.nFileSizeLow};
        ++*values[field];assert(!reader_image_identity_equal(expected,changed));
    }
    constexpr uint64_t base=0x140000000ULL;
    MEMORY_BASIC_INFORMATION memory{};memory.State=MEM_COMMIT;memory.Type=MEM_IMAGE;
    memory.AllocationBase=memory.BaseAddress=reinterpret_cast<void*>(base);
    assert(reader_module_mapping_valid(memory,base));
    for(unsigned field=0;field<4;++field){
        auto changed=memory;
        if(field==0)changed.State=MEM_RESERVE;
        if(field==1)changed.Type=MEM_PRIVATE;
        if(field==2)changed.AllocationBase=reinterpret_cast<void*>(base+4096);
        if(field==3)changed.BaseAddress=reinterpret_cast<void*>(base+4096);
        assert(!reader_module_mapping_valid(changed,base));
    }
    ReaderImageHeaders headers{};headers.dos.e_magic=IMAGE_DOS_SIGNATURE;headers.dos.e_lfanew=0x100;
    headers.nt.Signature=IMAGE_NT_SIGNATURE;headers.nt.OptionalHeader.SizeOfImage=166776832;
    headers.nt.OptionalHeader.ImageBase=base;
    assert(reader_image_headers_equal(headers,headers,base));
    auto changed=headers;++changed.dos.e_lfanew;assert(!reader_image_headers_equal(changed,headers,base));
    changed=headers;++changed.nt.OptionalHeader.SizeOfImage;assert(!reader_image_headers_equal(changed,headers,base));
    changed=headers;++changed.nt.FileHeader.TimeDateStamp;assert(!reader_image_headers_equal(changed,headers,base));
    changed=headers;changed.nt.OptionalHeader.ImageBase=base+4096;
    assert(!reader_image_headers_equal(changed,headers,base));
    assert(reader_image_headers_equal(changed,headers,base+4096));
    assert(reader_arguments({"--catalog-select","123","1:2:10000"},123));
    assert(!reader_arguments({"--catalog-select","124","1:2:10000"},123));
    assert(!reader_arguments({"--session"},123));
}
