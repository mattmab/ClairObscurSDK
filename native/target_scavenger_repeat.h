#pragma once
#include "scavenger_repeat_guard.h"

inline bool game_owned_repeat_active=false;
inline uint64_t game_owned_property(uint64_t base,uint64_t owner,const char* name,
                                   uint32_t offset,uint32_t width,uint64_t table,uint64_t flags) {
    auto field=local_read<uint64_t>(owner+0x50);
    for(unsigned i=0;field && i<128;++i,field=local_read<uint64_t>(field+0x18)) {
        if(!exact_name(base,field+0x20,name))continue;
        return local_read<uint64_t>(field)==base+table && local_read<uint64_t>(field+0x10)==(owner|1) &&
            local_read<uint32_t>(field+0x30)==1 && local_read<uint32_t>(field+0x34)==width &&
            local_read<uint64_t>(field+0x38)==flags && local_read<uint32_t>(field+0x44)==offset ? field:0;
    }
    return 0;
}
struct TargetScavengerRepeat {
    TargetGameOwnedCinematic admission;
    CallIdentity asset;
    uint64_t address=0;
    bool valid()const {
        const auto base=admission.base;
        if(local_read<DWORD>(base+0x9272d30)!=GetCurrentThreadId() || local_read<uint8_t>(base+0x9272cfc) ||
           local_read<uint8_t>(base+0x934e968) || !admission.original_scavenger(asset))return false;
        const auto cls=local_read<uint64_t>(asset.address+16);
        if(local_read<uint32_t>(cls+0x58)!=424)return false;
        const auto parameters=game_owned_property(base,cls,"CinematicParameters",48,336,0x6e136a0,0x8008000000005ULL);
        if(!parameters)return false;
        const auto type=local_read<uint64_t>(parameters+0x70);
        if(!admission.named(type,"S_TriggerCinematicVariables","/Game/Gameplay/CinematicSystem/S_TriggerCinematicVariables") ||
           local_read<uint32_t>(type+0x58)!=336 || local_read<uint64_t>(type+0x40))return false;
        const auto repeat=game_owned_property(base,type,"AllowRepeat_134_E017DD9E48ACD222B9BCF4BBEADAC35E",
            234,1,0x6e119b0,2251869606904325ULL);
        const auto restore_audio=game_owned_property(base,type,
            "RestoreExplorationSoundOnEnd_131_32363C8B49B23DC74291B2BD50570695",
            233,1,0x6e119b0,2251869606904325ULL);
        return repeat && restore_audio && local_read<uint32_t>(repeat+0x70)==0xff010001 &&
            local_read<uint32_t>(restore_audio+0x70)==0xff010001 &&
            asset.address<=UINT64_MAX-424 && address==asset.address+48+234;
    }
    bool read(uint8_t& repeat,uint8_t& restore_audio)const {
        repeat=local_read<uint8_t>(address);
        restore_audio=local_read<uint8_t>(address-1);
        return repeat<=1 && restore_audio<=1;
    }
    void write(uint8_t repeat,uint8_t restore_audio)const {
        *reinterpret_cast<volatile uint8_t*>(address)=repeat;
        *reinterpret_cast<volatile uint8_t*>(address-1)=restore_audio;
    }
};

// Keep SEH wrapper free of C++ objects requiring stack unwinding (C2712).
// Exact audited executor synchronously copies CinematicParameters into engine
// persistent state. Both shared source bytes are restored on normal return or SEH.
inline bool dispatch_scavenger_repeat(uint64_t dispatch,uint64_t object,uint64_t function,void* arguments,
                                      TargetScavengerRepeat* source,ScavengerRepeatGuard* guard) {
    bool restored=false;
    game_owned_repeat_active=true;
    __try {
        guard->apply(*source);
        reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(dispatch)(
            reinterpret_cast<void*>(object),reinterpret_cast<void*>(function),arguments);
    } __finally {
        restored=guard->restore(*source);
        // An uncertain restoration must not admit another invocation.
        if(restored)game_owned_repeat_active=false;
    }
    return restored;
}
