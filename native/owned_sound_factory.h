#pragma once
#include "invocation_protocol.h"
#include "owned_audio_limits.h"

// Build 23765773 CreateSound2D, verified in cinematic-sound-calls and the
// creation/defaults decompilations. The factory does not start playback:
// creation parameter +0x61 is zero. Ownership is adopted before its reply.
inline bool owned_sound_factory_contract(const CallPacket& p) {
    if(validate_call_packet(p) || p.entry_rva!=0x3736020 || p.function_flags!=67249163 ||
       p.parameter_size!=56 || p.return_offset!=48 || p.field_count!=9 || p.object_count!=2)
        return false;
    struct Field { const char* name; uint32_t kind,offset,width; uint64_t flags; };
    const Field expected[]={
        {"WorldContextObject",CallObject,0,8,6755468160533122ULL},
        {"Sound",CallObject,8,8,6755468160533120ULL},
        {"VolumeMultiplier",CallFloat,16,4,6759867280786048ULL},
        {"PitchMultiplier",CallFloat,20,4,6759867280786048ULL},
        {"StartTime",CallFloat,24,4,6759867280786048ULL},
        {"ConcurrencySettings",CallObject,32,8,6759866207044224ULL},
        {"bPersistAcrossLevelTransition",CallBool,40,1,6759867280786048ULL},
        {"bAutoDestroy",CallBool,41,1,6759867280786048ULL},
        {"ReturnValue",CallObject,48,8,6755468161058696ULL}
    };
    for(const auto& e:expected) {
        const CallField* found=nullptr;
        for(unsigned i=0;i<p.field_count;++i) if(!std::strcmp(p.fields[i].name,e.name)) found=&p.fields[i];
        if(!found || found->kind!=e.kind || found->offset!=e.offset || found->width!=e.width ||
           found->dimension!=1 || found->flags!=e.flags ||
           found->bool_encoding!=(e.kind==CallBool ? 0xff010001u : 0u)) return false;
    }
    bool world=false,sound=false;
    for(unsigned i=0;i<p.object_count;++i) {
        world |= p.objects[i].offset==0;
        sound |= p.objects[i].offset==8;
    }
    float volume{},pitch{},start{};
    std::memcpy(&volume,p.data+16,4); std::memcpy(&pitch,p.data+20,4); std::memcpy(&start,p.data+24,4);
    return world && sound && volume>=0 && volume<=kOwnedSoundVolumeMaximum && pitch>=.25f && pitch<=2 && start==0 &&
        !p.data[40] && !p.data[41];
}
