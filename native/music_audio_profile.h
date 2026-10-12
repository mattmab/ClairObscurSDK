#pragma once
#include "target_object_assignment.h"
#include "numbered_field_name.h"
#include "owned_audio_limits.h"

// Expedition 33 adapter profile, verified against sequence-music-owner-schema
// and the target FMapProperty/FArrayProperty exports. This is not a UE-wide ABI.
// Enumerates only the two declared strong-reference containers; no heap scan.
template<size_t Capacity>
struct MusicAudioReferenceSet {
    CallIdentity items[Capacity]{};
    uint32_t count=0;
    bool add(uint64_t base,uint64_t address,uint64_t audio_class,uint32_t limit=uint32_t(Capacity)) {
        if(count>Capacity || limit>Capacity) return false;
        if(!address) return true;
        for(unsigned i=0;i<count;++i) if(items[i].address==address) return true;
        if(count>=Capacity || count>=limit) return false;
        auto id=call_capture(base,address);
        if(!id.address || !call_derives(base,local_read<uint64_t>(address+0x10),audio_class)) return false;
        items[count++]=id; return true;
    }
};
using MusicAudioReferences=MusicAudioReferenceSet<kDiscoveredMusicCapacity>;
inline uint64_t music_field(uint64_t base,uint64_t owner,const char* name,uint32_t offset,
                            uint32_t width,uint64_t vtable,uint64_t flags,uint32_t name_number=0) {
    auto p=local_read<uint64_t>(owner+0x50);
    for(unsigned n=0;p && n<128;++n,p=local_read<uint64_t>(p+0x18)) {
        // Match both observed FName components. Existing callers still require
        // number zero; generated Blueprint locals explicitly declare theirs.
        if(!exact_field_name(base,p+0x20,name,name_number)) continue;
        return local_read<uint64_t>(p)==base+vtable && local_read<uint64_t>(p+0x10)==(owner|1) &&
            local_read<uint32_t>(p+0x30)==1 && local_read<uint32_t>(p+0x34)==width &&
            local_read<uint32_t>(p+0x44)==offset && local_read<uint64_t>(p+0x38)==flags ? p : 0;
    }
    return 0;
}
template<size_t Capacity>
inline bool music_audio_references(uint64_t base,const CallIdentity& system,const CallIdentity& audio,
                                   MusicAudioReferenceSet<Capacity>& out,uint32_t* detail=nullptr) {
    auto stage=[&](uint32_t value) { if(detail) *detail=value; };
    stage(1);
    if(out.count || !call_identity(base,system) || !call_identity(base,audio) ||
       !call_is_class(base,audio.address) || !exact_name(base,audio.address+0x18,"AudioComponent") ||
       !exact_name(base,local_read<uint64_t>(audio.address+0x20)+0x18,"/Script/Engine")) return false;
    stage(2);
    const auto cls=local_read<uint64_t>(system.address+0x10);
    if(!exact_name(base,cls+0x18,"BP_InteractiveMusicSystem_C") ||
       !exact_name(base,local_read<uint64_t>(cls+0x20)+0x18,"/Game/Gameplay/InteractiveMusic/BP_InteractiveMusicSystem")) return false;
    stage(3);
    const auto map=music_field(base,cls,"InteractiveMusicByContext",48,80,0x6e13370,549755879429ULL);
    const auto array=music_field(base,cls,"AudioComponentsToUnspawn",136,16,0x6e0de80,549755879429ULL);
    if(!map || !array || (local_read<uint8_t>(map+0x98)&1) || (local_read<uint8_t>(array+0x70)&1)) return false;
    stage(4);
    const auto key=local_read<uint64_t>(map+0x70), value=local_read<uint64_t>(map+0x78);
    const auto inner=local_read<uint64_t>(array+0x78);
    const auto value_offset=local_read<int32_t>(map+0x80), stride=local_read<int32_t>(map+0x8c);
    auto child=[&](uint64_t p,const char* type,uint64_t owner,uint32_t width,uint32_t offset) {
        return p && exact_name(base,local_read<uint64_t>(p+8),type) &&
            local_read<uint64_t>(p+0x10)==owner && local_read<uint32_t>(p+0x30)==1 &&
            local_read<uint32_t>(p+0x34)==width && local_read<uint32_t>(p+0x44)==offset;
    };
    if(value_offset<1 || value_offset>128 || stride<value_offset+24 || stride>256 ||
       !child(key,"ByteProperty",map,1,0) || !child(value,"StructProperty",map,24,uint32_t(value_offset)) ||
       !child(inner,"ObjectProperty",array,8,0) || local_read<uint64_t>(inner+0x70)!=audio.address) return false;
    stage(5);
    const auto structure=local_read<uint64_t>(value+0x70);
    if(!call_capture(base,structure).address || !exact_name(base,structure+0x18,"S_InteractiveMusic") ||
       !exact_name(base,local_read<uint64_t>(structure+0x20)+0x18,"/Game/Gameplay/InteractiveMusic/S_InteractiveMusic") ||
       local_read<uint32_t>(structure+0x58)!=24) return false;
    stage(6);
    const auto ref=music_field(base,structure,"AudioComponent_7_F10237DD43456A26DE6840B3DC60292D",0,8,0x6e11d38,2251868533686789ULL);
    if(!ref || local_read<uint64_t>(ref+0x70)!=audio.address) return false;
    stage(7);
    const auto at=system.address+48;
    const auto data=local_read<uint64_t>(at), heap=local_read<uint64_t>(at+32);
    const auto count=local_read<int32_t>(at+8), capacity=local_read<int32_t>(at+12);
    const auto bits=local_read<int32_t>(at+40), bit_capacity=local_read<int32_t>(at+44), free=local_read<int32_t>(at+52);
    if(count<0 || count>capacity || capacity>64 || bits!=count || bit_capacity<bits || bit_capacity>128 ||
       free<0 || free>count || (count && (!data || (data&7)))) return false;
    stage(8);
    unsigned live=0;
    for(int32_t i=0;i<count;++i) {
        if(!(local_read<uint32_t>((heap ? heap : at+16)+uint64_t(i/32)*4)&(1u<<(i%32)))) continue;
        ++live;
        if(!out.add(base,local_read<uint64_t>(data+uint64_t(i)*stride+value_offset),audio.address,kDiscoveredMusicCapacity)) return false;
    }
    stage(9);
    if(live!=unsigned(count-free)) return false;
    stage(10);
    const auto a=system.address+136, a_data=local_read<uint64_t>(a);
    const auto a_count=local_read<int32_t>(a+8), a_capacity=local_read<int32_t>(a+12);
    if(a_count<0 || a_count>a_capacity || a_capacity>64 || (a_count && (!a_data || (a_data&7)))) return false;
    stage(11);
    for(int32_t i=0;i<a_count;++i)
        if(!out.add(base,local_read<uint64_t>(a_data+uint64_t(i)*8),audio.address,kDiscoveredMusicCapacity)) return false;
    stage(0);return true;
}
