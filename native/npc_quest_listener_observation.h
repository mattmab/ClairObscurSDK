#pragma once
#include "npc_listener_observation.h"
namespace e33_npc_presentation {
struct QuestListenerObservation {CallIdentity system{};uint32_t total=0,owned=0;};
// Exact original Francois quest-condition subscription. The owner supplies
// independently retained nested targets. No delegate removal or invocation.
inline bool observe_quest_listeners(uint64_t b,CallIdentity game_instance,
        const CallIdentity* targets,size_t target_count,QuestListenerObservation& out){
    out={};
    if(!TargetPodSchemaOps{b}.context()||!call_identity(b,game_instance)||
       (local_read<uint32_t>(game_instance.address+8)&0x40018030U)||
       !e33_mesh::named(b,local_read<uint64_t>(game_instance.address+16),"BP_jRPG_GI_Custom_C",
                       "/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_GI_Custom"))return false;
    uint64_t descriptor=0;
    const auto at=picto_field(b,game_instance.address,"QuestSystem","ObjectProperty",3264,8,&descriptor);
    if(!at||!descriptor||local_read<uint64_t>(descriptor)!=b+0x6e11d38||
       local_read<uint64_t>(descriptor+0x38)!=0x8001000010205ULL||
       !e33_mesh::named(b,local_read<uint64_t>(descriptor+16)&~uint64_t(1),"BP_jRPG_GI_Custom_C",
                       "/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_GI_Custom"))return false;
    const auto cls=local_read<uint64_t>(descriptor+0x70);
    if(!e33_mesh::named(b,cls,"BP_QuestSystem_C","/Game/Gameplay/Quests/System/BP_QuestSystem"))return false;
    const auto system=call_capture(b,local_read<uint64_t>(at));
    if(!system.address||(local_read<uint32_t>(system.address+8)&0x40018030U)||
       local_read<uint64_t>(system.address+16)!=cls)return false;
    static constexpr ListenerField field={"OnAnyObjectiveStatusChanged","BP_QuestSystem_C",
        "/Game/Gameplay/Quests/System/BP_QuestSystem",176,0x100010010205ULL,0x6e13fc8ULL,
        "OnAnyObjectiveStatusChanged__DelegateSignature"};
    if(!observe_listener_field(b,system,field,targets,target_count,out.total,out.owned)||
       !call_identity(b,game_instance)||!call_identity(b,system)||local_read<uint64_t>(at)!=system.address)return false;
    out.system=system;return true;
}
}
