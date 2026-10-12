#pragma once
#include "retained_call_protocol.h"
#include <cmath>

// Only the observed native factory. Creation is not playback authorization.
constexpr uint32_t kSequenceCallVersion=7, kSequenceSettingsKind=18;
inline bool valid_sequence_settings(const uint8_t* value) {
    // No autoplay, looping, random start, input/HUD mutation or dynamic weights.
    // Tick while paused; force restoration of animated state on stop.
    for(unsigned i=0;i<40;++i)
        if(i!=16 && !(i>=20 && i<24) && i!=32 && value[i]) return false;
    float rate=0; std::memcpy(&rate,value+20,4);
    return value[16]==1 && value[32]==2 && std::isfinite(rate) && rate>=0.25f && rate<=2.0f;
}
inline uint32_t validate_sequence_call(const RetainedCallPacket& p) {
    const auto& c=p.call;
    if(!retained_call_empty(p) || c.version!=kSequenceCallVersion ||
       c.field_count!=5 || c.object_count!=2 || c.parameter_size!=72 ||
       c.allocation_extent!=72 || c.return_offset!=64 ||
       c.function_flags!=71443459 || c.entry_rva!=0x321b6a0) return 1460;
    const char* names[]={"WorldContextObject","LevelSequence","Settings","OutActor","ReturnValue"};
    const uint32_t offsets[]={0,8,16,56,64};
    const uint64_t flags[]={6755468160533120ULL,6755468160533120ULL,4503668346847360ULL,
                           6755468160533376ULL,6755468160534400ULL};
    for(unsigned i=0;i<5;++i) {
        const auto& f=c.fields[i];
        if(f.kind!=(i==2 ? kSequenceSettingsKind : CallObject) || std::strcmp(f.name,names[i]) ||
           f.offset!=offsets[i] || f.width!=(i==2 ? 40U : 8U) || f.dimension!=1 ||
           f.flags!=flags[i] || f.bool_encoding || f.constraint.index<0 || !f.constraint.address) return 1461;
    }
    if(c.objects[0].offset!=0 || c.objects[1].offset!=8 ||
       !valid_sequence_settings(c.data+16)) return 1462;
    auto normalized=c; normalized.version=2;
    normalized.fields[2].kind=CallUInt16;
    normalized.fields[2].width=2; normalized.fields[2].dimension=20;
    return validate_call_packet(normalized,true);
}
