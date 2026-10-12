#include "owned_sound_factory.h"
#include <cassert>
#include <cstdio>
#include <initializer_list>
int main() {
    CallPacket p{};
    p.version=1; p.parameter_size=p.allocation_extent=56; p.return_offset=48;
    p.function_flags=67249163; p.entry_rva=0x3736020;
    p.target=p.function={1,2,0x10000}; p.field_count=9; p.object_count=2;
    p.objects[0]={0,{2,3,0x20000}}; p.objects[1]={8,{3,4,0x30000}};
    const char* names[]={"WorldContextObject","Sound","VolumeMultiplier","PitchMultiplier","StartTime",
        "ConcurrencySettings","bPersistAcrossLevelTransition","bAutoDestroy","ReturnValue"};
    const uint32_t offsets[]={0,8,16,20,24,32,40,41,48};
    const uint64_t flags[]={6755468160533122ULL,6755468160533120ULL,6759867280786048ULL,
        6759867280786048ULL,6759867280786048ULL,6759866207044224ULL,6759867280786048ULL,
        6759867280786048ULL,6755468161058696ULL};
    for(unsigned i=0;i<9;++i) {
        auto& f=p.fields[i]; f.offset=offsets[i]; f.dimension=1; f.flags=flags[i];
        f.kind=i>=2 && i<=4 ? CallFloat : i==6 || i==7 ? CallBool : CallObject;
        f.width=f.kind==CallFloat ? 4 : f.kind==CallBool ? 1 : 8;
        if(f.kind==CallBool) f.bool_encoding=0xff010001;
        if(f.kind==CallObject) f.constraint={4,5,0x40000};
        std::memcpy(f.name,names[i],std::strlen(names[i])+1);
    }
    float one=1; std::memcpy(p.data+16,&one,4); std::memcpy(p.data+20,&one,4);
    assert(owned_sound_factory_contract(p));
#ifdef E33_EXTENDED_OWNED_AUDIO_SESSION
    float authored=2.f;std::memcpy(p.data+16,&authored,4);assert(owned_sound_factory_contract(p));
#else
    auto rejected=p;float authored=2.f;std::memcpy(rejected.data+16,&authored,4);assert(!owned_sound_factory_contract(rejected));
#endif
    auto bad=p; bad.data[40]=1; assert(!owned_sound_factory_contract(bad));
    bad=p; bad.data[41]=1; assert(!owned_sound_factory_contract(bad));
    bad=p; bad.entry_rva=0x3744750; assert(!owned_sound_factory_contract(bad)); // SpawnSound2D starts sound.
    bad=p; bad.objects[1].offset=32; assert(!owned_sound_factory_contract(bad));
    bad=p; bad.fields[8].flags^=0x800; assert(!owned_sound_factory_contract(bad));
    for(float invalid : {-1.f, 2.1f, INFINITY, NAN}) {
        bad=p; std::memcpy(bad.data+16,&invalid,4); assert(!owned_sound_factory_contract(bad));
    }
    bad=p; std::memcpy(bad.data+24,&one,4); assert(!owned_sound_factory_contract(bad));
    std::puts("Owned sound contract: factory, schema, ownership flags and input bounds passed.");
}
