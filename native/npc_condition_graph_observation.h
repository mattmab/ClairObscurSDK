#pragma once
#include "npc_listener_observation.h"
#include "npc_condition_graph.h"
namespace e33_npc_presentation {
inline bool condition_wrapper_contract(uint64_t b,uint64_t wrapper){
    if(!e33_mesh::named(b,wrapper,"ConditionChecker_Wrapper","/Script/SandFall")||
       local_read<int32_t>(wrapper+0x58)!=8)return false;
    const auto field=local_read<uint64_t>(wrapper+0x50);
    return field&&local_read<uint64_t>(field)==b+0x6e11d38&&local_read<uint64_t>(field+16)==(wrapper|1)&&
        exact_name(b,field+32,"ConditionChecker")&&local_read<int32_t>(field+0x30)==1&&
        local_read<int32_t>(field+0x34)==8&&local_read<int32_t>(field+0x44)==0&&
        local_read<uint64_t>(field+0x38)==0x1a00100008020dULL&&!local_read<uint64_t>(field+24);
}
inline int francois_condition_kind(uint64_t b,uint64_t cls){
    static constexpr const char* kinds[][2]={
        {"BP_ConditionChecker_BinaryLogicOperators_C","/Game/Gameplay/ConditionChecker/Logic/BP_ConditionChecker_BinaryLogicOperators"},
        {"BP_ConditionChecker_UnaryLogicOperators_C","/Game/Gameplay/ConditionChecker/Logic/BP_ConditionChecker_UnaryLogicOperators"},
        {"BP_ConditionChecker_PlayedDialogue_C","/Game/Gameplay/ConditionChecker/Dialogue/BP_ConditionChecker_PlayedDialogue"},
        {"BP_ConditionChecker_PersistentFlag_C","/Game/Gameplay/ConditionChecker/PersistentFlag/BP_ConditionChecker_PersistentFlag"},
        {"BP_ConditionChecker_QuestObjectiveStatus_C","/Game/Gameplay/ConditionChecker/Quest/BP_ConditionChecker_QuestObjectiveStatus"}};
    for(int i=0;i<5;++i)if(e33_mesh::named(b,cls,kinds[i][0],kinds[i][1]))return i;
    return -1;
}
template<class Visitor> struct FrancoisConditionGraphOps {
    uint64_t base;Visitor& visitor;
    bool retain_exact_owned(uint64_t object,uint64_t parent){
        const auto identity=call_capture(base,object);
        if(!identity.address||(local_read<uint32_t>(object+8)&0x40018030U)||
           local_read<uint64_t>(object+32)!=parent||
           francois_condition_kind(base,local_read<uint64_t>(object+16))<0)return false;
        return visitor(identity);
    }
    bool children(uint64_t object,uint64_t* children,size_t& count){
        count=0;
        const auto cls=local_read<uint64_t>(object+16);
        const auto kind=francois_condition_kind(base,cls);
        if(kind<0)return false;
        if(kind>=2)return true;
        uint64_t descriptor=0;
        const auto at=picto_field(base,object,kind==0?"Conditions":"Condition",kind==0?"ArrayProperty":"StructProperty",
                                  kind==0?104:96,kind==0?16:8,&descriptor);
        if(!at||!descriptor||local_read<uint64_t>(descriptor+16)!=(cls|1)||
           local_read<uint64_t>(descriptor)!=base+(kind==0?0x6e0de80:0x6e136a0)||
           local_read<uint64_t>(descriptor+0x38)!=(kind==0?0x8000000005ULL:0x9040000205ULL))return false;
        if(kind==1){
            if(!condition_wrapper_contract(base,local_read<uint64_t>(descriptor+0x70)))return false;
            children[0]=local_read<uint64_t>(at);count=1;return true;
        }
        const auto inner=local_read<uint64_t>(descriptor+0x78);
        if(!inner||local_read<uint64_t>(inner)!=base+0x6e136a0||local_read<uint64_t>(inner+16)!=descriptor||
           local_read<int32_t>(inner+0x30)!=1||local_read<int32_t>(inner+0x34)!=8||
           local_read<int32_t>(inner+0x44)!=0||!condition_wrapper_contract(base,local_read<uint64_t>(inner+0x70)))return false;
        const auto data=local_read<uint64_t>(at);
        const auto n=local_read<int32_t>(at+8),capacity=local_read<int32_t>(at+12);
        if(n!=2||capacity<n||capacity>8||data<0x10000||(data&7))return false;
        for(int i=0;i<n;++i)children[i]=local_read<uint64_t>(data+uint64_t(i)*8);
        count=size_t(n);return true;
    }
};
template<class Visitor> bool visit_francois_condition_roots(uint64_t b,CallIdentity actor,
        const CallIdentity* components,size_t component_count,Visitor& visitor){
    if(!TargetPodSchemaOps{b}.context()||!call_identity(b,actor)||!components||!component_count||component_count>8)return false;
    ConditionGraphEdge roots[8]{};
    for(size_t i=0;i<component_count;++i){
        const auto component=components[i];uint64_t descriptor=0;
        if(!call_identity(b,component)||local_read<uint64_t>(component.address+32)!=actor.address||
           !e33_mesh::named(b,local_read<uint64_t>(component.address+16),"BP_ConditionCheckerComponent_C",
                           "/Game/Gameplay/ConditionChecker/BP_ConditionCheckerComponent"))return false;
        const auto at=picto_field(b,component.address,"ConditionChecker","StructProperty",168,8,&descriptor);
        if(!at||!descriptor||local_read<uint64_t>(descriptor)!=b+0x6e136a0||
           local_read<uint64_t>(descriptor+0x38)!=0x9040000205ULL||
           !condition_wrapper_contract(b,local_read<uint64_t>(descriptor+0x70)))return false;
        roots[i]={local_read<uint64_t>(at),component.address};
    }
    FrancoisConditionGraphOps<Visitor> ops{b,visitor};
    return visit_owned_condition_graph(roots,component_count,ops)&&call_identity(b,actor);
}
}
