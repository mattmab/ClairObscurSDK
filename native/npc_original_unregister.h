#pragma once
#include "npc_presentation_admission.h"
#include "npc_unregister_once.h"
#include "npc_membership_observation.h"

// Internal bridge only: no arbitrary Blueprint-call or interface wire API.
// The NPC owner must supply its idle-battle guard and keep this journal alive
// through acknowledgement loss, SEH, destruction and final cleanup observation.
namespace e33_npc_presentation {
struct OriginalUnregisterField {
    const char* name;const char* type;int offset,width;uint64_t flags,table;
};
struct OriginalUnregisterProfile {
    const char* name;int extent,script_size;const OriginalUnregisterField* fields;size_t count;
};
#include "npc_unregister_profiles.inl"
enum class InteractionRegistry { Nearby, Distant };
struct UnregisterContext {
    CallIdentity controller,world,system,actor,actor_class,cdo,available,function;
    uint64_t session,lease;
};
inline bool unregister_function_contract(uint64_t b,CallIdentity function,uint64_t system_class,
        const OriginalUnregisterProfile& p){
    const auto fn=call_identity(b,function);
    if(!fn||local_read<uint64_t>(fn+32)!=system_class||
       !e33_mesh::named(b,local_read<uint64_t>(fn+16),"Function","/Script/CoreUObject")||
       !exact_name(b,fn+24,p.name)||local_read<uint32_t>(fn+0xb0)!=0xc820000||
       local_read<uint16_t>(fn+0xb6)!=16||local_read<uint16_t>(fn+0xb8)!=65535||
       local_read<int32_t>(fn+0x58)!=p.extent||local_read<uint64_t>(fn+0xd8)!=b+0x13937a0)return false;
    auto field=local_read<uint64_t>(fn+0x50);
    for(size_t i=0;i<p.count;++i){
        const auto& f=p.fields[i];
        if(!field||local_read<uint64_t>(field)!=b+f.table||local_read<uint64_t>(field+16)!=(fn|1)||
           !e33_mesh::candidate_name(b,field+32,f.name)||!exact_name(b,local_read<uint64_t>(field+8),f.type)||
           local_read<int32_t>(field+0x30)!=1||local_read<int32_t>(field+0x34)!=f.width||
           local_read<int32_t>(field+0x44)!=f.offset||local_read<uint64_t>(field+0x38)!=f.flags)return false;
        field=local_read<uint64_t>(field+24);
    }
    const auto data=local_read<uint64_t>(fn+0x60);
    const auto count=local_read<int32_t>(fn+0x68),capacity=local_read<int32_t>(fn+0x6c);
    return !field&&data>=0x10000&&count==p.script_size&&capacity>=count&&capacity<=65536;
}

template<class Pool,class IdleGuard> struct OriginalUnregisterOps {
    uint64_t base;const UnregisterContext& context;InteractionRegistry registry;Pool& pool;IdleGuard& idle;
    uint64_t process_event=0;
    struct InterfaceValue {uint64_t object=0,interface_pointer=0;} argument{};
    bool validate(){
        const auto b=base;const auto& c=context;
        if((registry!=InteractionRegistry::Nearby&&registry!=InteractionRegistry::Distant)||
           !TargetPodSchemaOps{b}.context()||!c.session||!c.lease||!idle()||
           !call_identity(b,c.controller)||!call_identity(b,c.world)||!call_identity(b,c.system)||
           !e33_mesh::named(b,local_read<uint64_t>(c.world.address+16),"World","/Script/Engine")||
           !call_identity(b,c.actor)||!pool.owns_object(c.session,c.lease,c.actor.address)||
           !presentation_class_contract(b,c.actor_class,c.cdo,c.available)||
           local_read<uint64_t>(c.actor.address+16)!=c.actor_class.address||
           (local_read<uint32_t>(c.actor.address+8)&0x30))return false;
        // Both actor and controller must belong to the exact observed world.
        for(const auto object:{c.controller.address,c.actor.address}){
            auto outer=object;unsigned outer_depth=0;
            for(;outer&&outer!=c.world.address&&++outer_depth<32;outer=local_read<uint64_t>(outer+32)){}
            if(outer!=c.world.address)return false;
        }
        const auto cls=local_read<uint64_t>(c.system.address+16);
        if(!e33_mesh::named(b,cls,"BP_InteractionSystem_C","/Game/Gameplay/Exploration/BP_InteractionSystem")||
           (local_read<uint32_t>(c.system.address+8)&0x30)||local_read<uint64_t>(c.system.address+32)!=c.controller.address)return false;
        const bool distant=registry==InteractionRegistry::Distant;
        const auto& profile=distant?unregister_profile_1:unregister_profile_0;
        if(!unregister_function_contract(b,c.function,cls,profile))return false;
        // Original unregister also updates active/displayed prompts. Recover
        // only the exact owned registered pair across all five locations,
        // including when the actor has already left its source array.
        MembershipObservation membership{};
        if(!observe_memberships(b,c.system,c.controller,c.actor,membership))return false;
        argument={membership.owned_interface.object,membership.owned_interface.interface_pointer};
        // Never synthesize a native interface pointer. Script-only interfaces
        // may legitimately have a null second word; preserve the actual pair.
        process_event=local_read<uint64_t>(local_read<uint64_t>(c.system.address)+0x268);
        return (process_event==b+0x1393330||process_event==b+0x332bb90)&&
            call_identity(b,c.actor)&&call_identity(b,c.system)&&call_identity(b,c.function)&&idle();
    }
    bool dispatch_once(){
        if(argument.object)reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(process_event)(
            reinterpret_cast<void*>(context.system.address),reinterpret_cast<void*>(context.function.address),&argument);
        // A void original call returning is acknowledgement, not cleanup proof.
        // Absence in this array alone also does not prove prompt/listener cleanup.
        return true;
    }
};
template<class Pool,class IdleGuard> UnregisterResult unregister_original(uint64_t base,
        const UnregisterContext& context,InteractionRegistry registry,Pool& pool,IdleGuard& idle,UnregisterJournal& journal){
    OriginalUnregisterOps<Pool,IdleGuard> ops{base,context,registry,pool,idle};
    return journal.run(ops);
}
}
