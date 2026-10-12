#pragma once
#include "music_audio_profile.h"
#include "cinematic_script_shape.h"

// Exact build-specific getter admission. Never accepts caller-supplied offsets
// or uses function names alone as permission to mutate a return value.
inline bool cinematic_getter_profile(uint64_t base,const CallIdentity& getter_id,
                                    const CallIdentity& native_id,const CallIdentity& library_id,
                                    const CallIdentity& component_id,uint64_t& script_out,uint64_t* return_property=nullptr) {
    script_out=0;if(return_property) *return_property=0;
    const auto getter=call_identity(base,getter_id), native=call_identity(base,native_id);
    const auto library=call_identity(base,library_id), component=call_identity(base,component_id);
    if(!getter || !native || !library || !component ||
       !exact_name(base,getter+0x18,"GetCinematicsSystem") ||
       local_read<uint32_t>(getter+0xb0)!=0x1c422000 || local_read<uint16_t>(getter+0xb6)!=16 ||
       local_read<uint16_t>(getter+0xb8)!=8 || local_read<uint64_t>(getter+0xd8)!=base+0x13937a0 ||
       local_read<uint32_t>(getter+0x58)!=32) return false;
    const auto owner=local_read<uint64_t>(getter+0x20), cls=local_read<uint64_t>(component+0x10);
    if(!call_is_class(base,owner) || local_read<uint64_t>(library+0x10)!=owner ||
       !(local_read<uint32_t>(library+8)&0x10) ||
       !exact_name(base,owner+0x18,"FL_jRPG_CustomFunctionLibrary_C") ||
       !exact_name(base,local_read<uint64_t>(owner+0x20)+0x18,
          "/Game/jRPGTemplate/Blueprints/Basics/FL_jRPG_CustomFunctionLibrary") ||
       !exact_name(base,cls+0x18,"BP_CinematicSystem_C") ||
       !exact_name(base,local_read<uint64_t>(cls+0x20)+0x18,
          "/Game/Gameplay/CinematicSystem/BP_CinematicSystem") ||
       !exact_name(base,native+0x18,"GetComponentByClass") ||
       local_read<uint64_t>(native+0xd8)!=base+0x333a230 ||
       local_read<uint32_t>(native+0xb0)!=0x54020403 ||
       local_read<uint16_t>(native+0xb6)!=16 || local_read<uint16_t>(native+0xb8)!=8) return false;
    const auto actor=local_read<uint64_t>(native+0x20);
    if(!exact_name(base,actor+0x18,"Actor") ||
       !exact_name(base,local_read<uint64_t>(actor+0x20)+0x18,"/Script/Engine")) return false;
    const auto world=music_field(base,getter,"__WorldContext",0,8,0x6e11d38,0x8001000000294ULL);
    const auto ret=music_field(base,getter,"ReturnValue",8,8,0x6e11d38,0x8001000080780ULL);
    const auto pc=music_field(base,getter,"CallFunc_GetPlayerController_ReturnValue",16,8,0x6e11d38,0x8001000000200ULL);
    const auto comp=music_field(base,getter,"CallFunc_GetComponentByClass_ReturnValue",24,8,0x6e11d38,0x8001000080200ULL);
    if(!world || !ret || !pc || !comp || local_read<uint64_t>(ret+0x70)!=cls ||
       local_read<uint64_t>(comp+0x70)!=cls) return false;
    const auto script=local_read<uint64_t>(getter+0x60);
    const auto count=local_read<int32_t>(getter+0x68),capacity=local_read<int32_t>(getter+0x6c);
    if(!script || count!=115 || capacity<count || capacity>65536) return false;
    const auto controller=local_read<uint64_t>(script+11);
    if(!call_capture(base,controller).address || !exact_name(base,controller+0x18,"GetPlayerController")) return false;
    const auto statics=local_read<uint64_t>(controller+0x20);
    if(!exact_name(base,statics+0x18,"GameplayStatics") ||
       !exact_name(base,local_read<uint64_t>(statics+0x20)+0x18,"/Script/Engine")) return false;
    const uint32_t offsets[]={2,11,20,36,46,58,67,76,87,96,106};
    const uint64_t values[]={pc,controller,world,comp,pc,comp,native,cls,ret,comp,ret};
    const uint8_t expected[]={
        0x5f,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x68,0x00,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x1d,0x00,0x00,0x00,
        0x00,0x16,0x5f,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x19,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x00,0x00,0x13,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        0x00,0x00,0x1c,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x20,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x16,0x5f,0x48,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x04,0x48,0x00,0x00,0x00,0x00,0x00,0x00,
        0x00,0x00,0x53
    };
    static_assert(sizeof(expected)==115);
    auto read=[](uint64_t address,void* output,size_t size) {
        std::memcpy(output,reinterpret_cast<const void*>(address),size);return true;
    };
    if(!e33_cinematic::exact_script_shape(read,script,expected,offsets,values)) return false;
    script_out=script;if(return_property) *return_property=ret;return true;
}
