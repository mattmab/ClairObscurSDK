#pragma once
#include "mesh_owner.h"
#include "picto_progression.h"
#include "npc_listener_targets.h"
namespace e33_npc_presentation {
struct ListenerField {const char* name;const char* owner;const char* package;int offset;uint64_t flags,table;const char* signature;};
#include "npc_listener_profiles.inl"
struct ListenerObservation {uint32_t total[23]{},owned[23]{};bool absent()const{for(const auto n:owned)if(n)return false;return true;}};
struct ListenerStorageOps {
    bool read(uint64_t at,int32_t& index,int32_t& serial){
        index=local_read<int32_t>(at);serial=local_read<int32_t>(at+4);return true;
    }
};
inline bool observe_listener_field(uint64_t b,CallIdentity recipient,const ListenerField& expected,
        const CallIdentity* targets,size_t target_count,uint32_t& total,uint32_t& owned){
    total=0;owned=0;uint64_t descriptor=0;
    const auto at=picto_field(b,recipient.address,expected.name,"MulticastInlineDelegateProperty",expected.offset,16,&descriptor);
    if(!at||!descriptor||local_read<uint64_t>(descriptor)!=b+expected.table||
       local_read<uint64_t>(descriptor+0x38)!=expected.flags||
       !e33_mesh::named(b,local_read<uint64_t>(descriptor+16)&~uint64_t(1),expected.owner,expected.package))return false;
    const auto signature=local_read<uint64_t>(descriptor+0x70);
    if(!call_capture(b,signature).address||!exact_name(b,signature+24,expected.signature))return false;
    ListenerStorageOps entries;
    return count_listener_targets(local_read<uint64_t>(at),local_read<int32_t>(at+8),local_read<int32_t>(at+12),
                                  targets,target_count,entries,total,owned);
}
// Read-only FMulticastScriptDelegate storage for this exact supported build.
// No general DelegateProperty codec, invocation, clearing or pruning operation.
inline bool observe_listeners(uint64_t b,CallIdentity game_instance,const CallIdentity* targets,size_t target_count,ListenerObservation& out){
    out={};
    if(!TargetPodSchemaOps{b}.context()||!call_identity(b,game_instance)||!targets||!target_count||target_count>128||
       (local_read<uint32_t>(game_instance.address+8)&0x40018030U)||
       !e33_mesh::named(b,local_read<uint64_t>(game_instance.address+16),"BP_jRPG_GI_Custom_C",
           "/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_GI_Custom"))return false;
    for(size_t i=0;i<target_count;++i){
        if(targets[i].index<0||targets[i].serial<=0||targets[i].address<0x10000)return false;
        for(size_t j=0;j<i;++j)if(targets[j].index==targets[i].index||targets[j].address==targets[i].address)return false;
    }
    for(size_t field_index=0;field_index<23;++field_index){
        if(!observe_listener_field(b,game_instance,listener_fields[field_index],targets,target_count,
                                  out.total[field_index],out.owned[field_index]))return false;
    }
    return call_identity(b,game_instance)!=0;
}
inline bool empty_condition_wrapper(uint64_t b,CallIdentity component){
    if(!TargetPodSchemaOps{b}.context()||!call_identity(b,component)||
       !e33_mesh::named(b,local_read<uint64_t>(component.address+16),"BP_ConditionCheckerComponent_C",
           "/Game/Gameplay/ConditionChecker/BP_ConditionCheckerComponent"))return false;
    uint64_t descriptor=0;
    const auto at=picto_field(b,component.address,"ConditionChecker","StructProperty",168,8,&descriptor);
    if(!at||!descriptor||local_read<uint64_t>(descriptor)!=b+0x6e136a0||
       local_read<uint64_t>(descriptor+0x38)!=0x9040000205ULL)return false;
    const auto wrapper=local_read<uint64_t>(descriptor+0x70);
    if(!e33_mesh::named(b,wrapper,"ConditionChecker_Wrapper","/Script/SandFall")||local_read<int32_t>(wrapper+0x58)!=8)return false;
    const auto field=local_read<uint64_t>(wrapper+0x50);
    return field&&local_read<uint64_t>(field)==b+0x6e11d38&&local_read<uint64_t>(field+16)==(wrapper|1)&&
        exact_name(b,field+32,"ConditionChecker")&&local_read<int32_t>(field+0x30)==1&&local_read<int32_t>(field+0x34)==8&&
        local_read<int32_t>(field+0x44)==0&&local_read<uint64_t>(field+0x38)==0x1a00100008020dULL&&
        !local_read<uint64_t>(field+24)&&!local_read<uint64_t>(at);
}
}
