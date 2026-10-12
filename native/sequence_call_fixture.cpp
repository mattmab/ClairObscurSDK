#include "sequence_call_protocol.h"
#include "target_pod_schema.h"
#include "sequence_settings_schema.h"
#include <cassert>
#include <iostream>

// Compile the live adapter together with the recursive schema gate. This is
// not a substitute for the eventual game-thread preflight against real fields.
bool compile_sequence_settings(uint64_t base,const CallIdentity& id) {
    TargetPodSchemaOps ops{base};
    return sequence_settings_schema(ops,id,"MovieSceneSequencePlaybackSettings");
}
int main() {
    RetainedCallPacket p{}; auto& c=p.call;
    c.version=7; c.target=c.function={1,2,0x10000};
    c.parameter_size=c.allocation_extent=72; c.return_offset=64;
    c.function_flags=71443459; c.entry_rva=0x321b6a0;
    c.field_count=5; c.object_count=2;
    c.objects[0]={0,{2,3,0x20000}}; c.objects[1]={8,{3,4,0x30000}};
    const char* names[]={"WorldContextObject","LevelSequence","Settings","OutActor","ReturnValue"};
    const uint32_t offsets[]={0,8,16,56,64};
    const uint64_t flags[]={6755468160533120ULL,6755468160533120ULL,4503668346847360ULL,
        6755468160533376ULL,6755468160534400ULL};
    for(unsigned i=0;i<5;++i) {
        auto& f=c.fields[i]; f.kind=i==2 ? kSequenceSettingsKind : CallObject;
        f.offset=offsets[i]; f.width=i==2 ? 40 : 8; f.dimension=1; f.flags=flags[i];
        f.constraint={4,5,0x40000}; std::memcpy(f.name,names[i],std::strlen(names[i])+1);
    }
    c.data[32]=1; c.data[48]=2;
    float rate=1.0f; std::memcpy(c.data+36,&rate,4);
    assert(!validate_sequence_call(p));
    for(unsigned i=0;i<40;++i) {
        if(i>=20 && i<24) continue;
        auto bad=p; bad.call.data[16+i]^=0x80; assert(validate_sequence_call(bad));
    }
    for(float invalid: {0.0f,0.24f,2.01f,INFINITY,NAN}) {
        auto bad=p; std::memcpy(bad.call.data+36,&invalid,4); assert(validate_sequence_call(bad));
    }
    auto bad=p; bad.call.objects[1].offset=56; assert(validate_sequence_call(bad));
    bad=p; bad.call.entry_rva++; assert(validate_sequence_call(bad));
    bad=p; bad.call.fields[2].flags|=0x100; assert(validate_sequence_call(bad));
    bad=p; bad.count=1; assert(validate_sequence_call(bad));
    assert(validate_call_packet(c,true)); // Existing protocol cannot accept it.
    std::cout<<"sequence creation envelope guards passed\n";
}
