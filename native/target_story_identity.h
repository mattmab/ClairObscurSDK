#pragma once
#include "story_identity_protocol.h"
#include "story_identity_engine_bytes.h"
#include "retired_world_target.h"
namespace e33_story_identity {
inline bool snapshot(uint64_t map,uint64_t descriptor,std::vector<Entry>& out){
    if(local_read<uint8_t>(descriptor+0x98)&1)return false;
    if(local_read<int32_t>(descriptor+0x80)!=16||local_read<int32_t>(descriptor+0x84)!=20||
       local_read<int32_t>(descriptor+0x88)!=24||local_read<int32_t>(descriptor+0x8c)!=28)return false;
    const auto count=local_read<int32_t>(map+8),cap=local_read<int32_t>(map+12),bits=local_read<int32_t>(map+40),
        bitcap=local_read<int32_t>(map+44),free=local_read<int32_t>(map+52),size=local_read<int32_t>(map+72);
    const auto data=local_read<uint64_t>(map),heap=local_read<uint64_t>(map+32),mask=heap?heap:map+16,
        hashes=local_read<uint64_t>(map+64),buckets=hashes?hashes:map+56;
    if(count<0||count>cap||cap>8192||bits!=count||bitcap<bits||bitcap>16384||free<0||free>count||
       (!heap&&bitcap>128)||(count&&(!data||(data&3)))||size<0||size>16384||
       (size&&(size&(size-1)))||(!hashes&&size>2))return false;
    std::vector<uint8_t> seen(size_t(count),0);int live=0;
    for(int bucket=0;bucket<size;++bucket){
        int index=local_read<int32_t>(buckets+uint64_t(bucket)*4);
        for(int n=0;index!=-1;++n){
            if(index<0||index>=count||n>=count||seen[size_t(index)]||
               !(local_read<uint32_t>(mask+uint64_t(index/32)*4)&(uint32_t(1)<<(index%32))))return false;
            const auto at=data+uint64_t(index)*28;
            if((local_read<uint32_t>(at+24)&uint32_t(size-1))!=uint32_t(bucket))return false;
            seen[size_t(index)]=1;++live;Entry e{};std::memcpy(&e,reinterpret_cast<void*>(at),20);out.push_back(e);
            index=local_read<int32_t>(at+20);
        }
    }
    return live==count-free&&normalize(out);
}
struct Dispatcher {
    bool unknown=false;
    template<class Pool> void run(uint64_t b,uint64_t session,Pool& leases,Packet&p){
        if(unknown){p.error=uncertain;return;}
        e33_retired_world::TargetOps proof{b};
        if(!valid(p)||!proof.current_binding(p.engine,p.viewport,p.world)||!proof.controller_world(p.controller,p.world)||
           !call_identity(b,p.gi)||!leases.owns_object(session,p.lease,p.gi.address)||
           !picto_class(b,p.gi.address,"BP_jRPG_GI_Custom_C","/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_GI_Custom")||
           zone_ref(b,p.world.address,"OwningGameInstance")!=p.gi.address){p.error=rejected;return;}
        const auto manager=zone_ref(b,p.gi.address,"SaveManager");uint64_t loaded_descriptor=0,loading_descriptor=0;
        const auto loaded=picto_field(b,p.gi.address,"SaveLoaded","BoolProperty",2680,1,&loaded_descriptor),
            loading=manager?picto_field(b,manager,"LoadIsInProgress","BoolProperty",169,1,&loading_descriptor):0;
        if(!manager||!picto_class(b,manager,"BP_SaveManager_C","/Game/Gameplay/Save/BP_SaveManager")||
           zone_ref(b,manager,"GameInstanceReference")!=p.gi.address||!loaded||!loading||
           local_read<uint32_t>(loaded_descriptor+0x70)!=0xff010001U||local_read<uint32_t>(loading_descriptor+0x70)!=0xff010001U||
           local_read<uint8_t>(loaded)!=1||local_read<uint8_t>(loading)!=0){p.error=rejected;return;}
        const auto function=call_identity(b,p.function);
        if(!function||!e33_mesh::named(b,function,"Map_Add","BlueprintMapLibrary")||
           local_read<uint64_t>(function+0xd8)!=b+0x34cba80||
           std::memcmp(reinterpret_cast<void*>(b+0x34a7a80),generic_map_add_code,sizeof(generic_map_add_code))||
           std::memcmp(reinterpret_cast<void*>(b+0x34cbc7f),generic_map_add_call,sizeof(generic_map_add_call))){p.error=rejected;return;}
        uint64_t descriptor=0;const auto map=picto_field(b,p.gi.address,"InteractedDialogues","MapProperty",3400,80,&descriptor);
        const auto key=descriptor?local_read<uint64_t>(descriptor+0x70):0,value=descriptor?local_read<uint64_t>(descriptor+0x78):0;
        if(!map||!key||!value||local_read<uint64_t>(key+16)!=descriptor||local_read<uint64_t>(value+16)!=descriptor||
           !exact_name(b,local_read<uint64_t>(key+8),"StructProperty")||!exact_name(b,local_read<uint64_t>(value+8),"IntProperty")||
           local_read<int32_t>(key+0x34)!=16||local_read<int32_t>(value+0x34)!=4||local_read<int32_t>(key+0x44)!=0||
           local_read<int32_t>(value+0x44)!=16||!e33_mesh::named(b,local_read<uint64_t>(key+0x70),"Guid","/Script/CoreUObject")){
            p.error=rejected;return;
        }
        std::vector<Entry> before;Entry existing{},desired{};std::memcpy(desired.guid,p.guid,16);desired.value=stage;
        if(!snapshot(map,descriptor,before)){p.error=rejected;return;}
        const int found=marker(before,existing);
#if E33_RUNTIME_CINEMATIC_VERSION>=270
        if(!p.mode){
            read_marker(p,before);return;
        }
#endif
        if(found<0||(found&& !same_key(existing,desired))){p.error=rejected;return;}
        if(found){p.state=1;return;}
        if(!p.mode){p.state=2;return;}
        // Latch before dispatch. Any fault or unverifiable readback prevents a
        // second mutation in this SDK session; no campaign delegates are run.
        unknown=true;
        reinterpret_cast<void(__fastcall*)(void*,void*,const void*,const void*)>(b+0x34a7a80)(
            reinterpret_cast<void*>(map),reinterpret_cast<void*>(descriptor),desired.guid,&desired.value);
        std::vector<Entry> after;
        if(!snapshot(map,descriptor,after)||!preserves(before,after,desired)){p.error=uncertain;return;}
        unknown=false;p.state=1;
    }
};
}
