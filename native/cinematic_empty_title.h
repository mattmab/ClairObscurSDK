#pragma once
#include "music_audio_profile.h"

// Exact BackAtCamp root only. No child sequences, event elements or bindings
// are traversed. The caller executes this on the game thread before creation
// and again immediately before the owned player's native Play dispatch.
namespace e33_empty_title {
inline bool named(uint64_t base,uint64_t value,const char* name,const char* package) {
    return call_capture(base,value).address && !(local_read<uint32_t>(value+8)&0x40000000) && exact_name(base,value+24,name) &&
        exact_name(base,local_read<uint64_t>(value+32)+24,package);
}
inline bool is_back_at_camp(uint64_t base,const CallIdentity& id) {
    return call_identity(base,id) && named(base,id.address,"LS_Title_BackAtCamp",
        "/Game/Cinematics/Titles/SequenceTitles/LS_Title_BackAtCamp");
}
struct Array { uint64_t data; int32_t count,capacity; };
static_assert(sizeof(Array)==16);
inline bool array_shape(const Array& a,int32_t maximum) {
    return a.count>=0 && a.capacity>=a.count && a.capacity<=maximum &&
        (!a.count || (a.data && !(a.data&7)));
}
inline uint64_t array_property(uint64_t base,uint64_t cls,const char* name,
        uint32_t offset,uint64_t flags,const char* inner_name,uint32_t inner_size,bool object) {
    const auto p=music_field(base,cls,name,offset,16,0x6e0de80,flags);
    if(!p || (local_read<uint8_t>(p+112)&1)) return 0;
    const auto child=local_read<uint64_t>(p+120);
    if(!child || child==p || local_read<uint64_t>(child)!=base+(object?0x6e11d38:0x6e136a0) ||
        local_read<uint64_t>(child+16)!=p || local_read<uint32_t>(child+48)!=1 ||
        local_read<uint32_t>(child+52)!=inner_size || local_read<uint32_t>(child+68)) return 0;
    const auto type=local_read<uint64_t>(child+112);
    return named(base,type,inner_name,"/Script/MovieScene") ? p : 0;
}
inline bool empty_channel(uint64_t base,uint64_t section,uint64_t cls) {
    const auto field=music_field(base,cls,"EventChannel",248,248,0x6e136a0,0x10000000000000ULL);
    if(!field) return false;
    const auto type=local_read<uint64_t>(field+112);
    if(!named(base,type,"MovieSceneEventChannel","/Script/MovieSceneTracks") ||
       local_read<uint32_t>(type+88)!=248) return false;
    // Exact nested layout confirmed in coverage-backatcamp-channel.json.
    uint64_t fields[2]{}; uint32_t offsets[2]{};
    const char* names[]={"KeyTimes","KeyValues"};
    const char* inner_names[]={"FrameNumber","MovieSceneEvent"};
    const char* packages[]={"/Script/CoreUObject","/Script/MovieSceneTracks"};
    for(unsigned i=0;i<2;++i) {
        auto cursor=local_read<uint64_t>(type+80);
        for(unsigned n=0;cursor && n<128;++n,cursor=local_read<uint64_t>(cursor+24)) {
            if(!exact_field_name(base,cursor+32,names[i],0)) continue;
            if(fields[i]) return false;
            fields[i]=cursor;
        }
        if(cursor) return false;
        const auto p=fields[i];
        if(!p || local_read<uint64_t>(p)!=base+0x6e0de80 || local_read<uint64_t>(p+16)!=(type|1) ||
           local_read<uint32_t>(p+48)!=1 || local_read<uint32_t>(p+52)!=16 ||
           (local_read<uint8_t>(p+112)&1)) return false;
        offsets[i]=local_read<uint32_t>(p+68);
        if(offsets[i]!=(i==0 ? 80u : 96u) || local_read<uint64_t>(p+56)!=0x40000000000200ULL) return false;
        const auto child=local_read<uint64_t>(p+120);
        if(!child || child==p || local_read<uint64_t>(child)!=base+0x6e136a0 ||
           local_read<uint64_t>(child+16)!=p || local_read<uint32_t>(child+48)!=1 ||
           local_read<uint32_t>(child+68)) return false;
        const auto inner=local_read<uint64_t>(child+112);
        if(!named(base,inner,inner_names[i],packages[i]) ||
           local_read<uint32_t>(inner+88)!=(i==0 ? 4u : 40u) ||
           local_read<uint32_t>(child+52)!=local_read<uint32_t>(inner+88)) return false;
    }
    if(offsets[0]+16>offsets[1] && offsets[1]+16>offsets[0]) return false;
    for(unsigned i=0;i<2;++i) {
        const auto a=local_read<Array>(section+248+offsets[i]);
        if(!array_shape(a,1048576) || a.count) return false;
    }
    return true;
}
inline bool validate(uint64_t base,const CallIdentity& sequence) {
    if(GetCurrentThreadId()!=local_read<DWORD>(base+0x9272d30) || !is_back_at_camp(base,sequence)) return false;
    const auto cls=local_read<uint64_t>(sequence.address+16);
    if(!named(base,cls,"LevelSequence","/Script/LevelSequence") ||
       !music_field(base,cls,"MovieScene",112,8,0x6e11d38,0x11c001000080208ULL)) return false;
    const auto scene=local_read<uint64_t>(sequence.address+112);
    if(!call_capture(base,scene).address || local_read<uint64_t>(scene+32)!=sequence.address) return false;
    const auto sc=local_read<uint64_t>(scene+16);
    if(!named(base,sc,"MovieScene","/Script/MovieScene")) return false;
    const char* empty_names[]={"Spawnables","Possessables","ObjectBindings"};
    const char* inner_names[]={"MovieSceneSpawnable","MovieScenePossessable","MovieSceneBinding"};
    const uint32_t sizes[]={240,128,48};
    for(unsigned i=0;i<3;++i) {
        if(!array_property(base,sc,empty_names[i],96+i*16,
                i==2?0x40008000000200ULL:0x40000000000200ULL,inner_names[i],sizes[i],false)) return false;
        const auto a=local_read<Array>(scene+96+i*16);
        if(!array_shape(a,1024) || a.count) return false;
    }
    if(!music_field(base,sc,"CameraCutTrack",240,8,0x6e11d38,0x14e001000080208ULL) ||
       local_read<uint64_t>(scene+240) ||
       !array_property(base,sc,"Tracks",224,0x144008000000208ULL,"MovieSceneTrack",8,true)) return false;
    const auto tracks=local_read<Array>(scene+224);
    if(!array_shape(tracks,16) || tracks.count!=4) return false;
    unsigned mask=0;
    for(int32_t i=0;i<tracks.count;++i) {
        const auto track=local_read<uint64_t>(tracks.data+uint64_t(i)*8);
        if(!call_capture(base,track).address || local_read<uint64_t>(track+32)!=scene) return false;
        const auto tc=local_read<uint64_t>(track+16);
        unsigned bit=0;
        if(named(base,tc,"MovieSceneFadeTrack","/Script/MovieSceneTracks")) bit=1;
        else if(named(base,tc,"BP_WidgetSequencerTrack_C","/Game/Gameplay/UI/Sequencer/BP_WidgetSequencerTrack")) bit=2;
        else if(named(base,tc,"BP_InteractiveMusicSequencerTrack_C","/Game/Gameplay/InteractiveMusic/Sequencer/BP_InteractiveMusicSequencerTrack")) bit=4;
        else if(named(base,tc,"MovieSceneEventTrack","/Script/MovieSceneTracks")) bit=8;
        if(!bit || (mask&bit)) return false;
        mask|=bit;
        if(bit!=8) continue;
        if(!array_property(base,tc,"Sections",176,0x144008000000208ULL,"MovieSceneSection",8,true)) return false;
        const auto sections=local_read<Array>(track+176);
        if(!array_shape(sections,16) || sections.count!=1) return false;
        const auto section=local_read<uint64_t>(sections.data);
        if(!call_capture(base,section).address || local_read<uint64_t>(section+32)!=track) return false;
        const auto section_class=local_read<uint64_t>(section+16);
        if(!named(base,section_class,"MovieSceneEventTriggerSection","/Script/MovieSceneTracks") ||
           !empty_channel(base,section,section_class)) return false;
    }
    return mask==15 && call_identity(base,sequence);
}
}


