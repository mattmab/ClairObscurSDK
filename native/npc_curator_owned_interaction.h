#pragma once
#include "npc_interaction_isolation.h"
#include "scalar_assignment.h"
#include "mesh_owner.h"

namespace e33_npc_presentation {
// Narrow adapter to the existing SDK scalar primitive. The containing owner
// must still prove the complete original function/reference contract; this
// adapter does not extend original_class_contract or grant spawn admission.
template<class Pool,class Guard> struct CuratorOwnedInteractionOps {
    uint64_t base,session,actor_lease;
    Pool& pool;Guard& guard;
    CallIdentity actor,field_owner,available;
    InteractionIsolationIdentity owned_identity(){return {actor.index,actor.serial,actor.address};}
    bool owns_identity(InteractionIsolationIdentity observed){
        if(observed.index!=actor.index||observed.serial!=actor.serial||observed.address!=actor.address||
           !session||!actor_lease||!TargetObjectAssignmentOps{base}.context()||
           !guard.current_context()||!guard.battle_quiescent()||!call_identity(base,actor)||
           (local_read<uint32_t>(actor.address+8)&0x30)||
           !pool.owns_object(session,actor_lease,actor.address))return false;
        const auto cls=local_read<uint64_t>(actor.address+16);
#if E33_RUNTIME_CINEMATIC_VERSION >= 168
        if(e33_mesh::named(base,cls,"BP_NPC_FrancoisTheTurtle_C",
            "/Game/Characters/Enemies/Esquies_Nest/Francois/BP_NPC_FrancoisTheTurtle"))return true;
#endif
        return e33_mesh::named(base,cls,"BP_Character_Camp_Curator_C","/Game/Characters/Heros/Camps/BP_Character_Camp_Curator")||
            e33_mesh::named(base,cls,"BP_Character_NPC_Curator_C","/Game/Characters/NPCs/Spirits/Curator/BP_Character_NPC_Curator");
    }
    ScalarAssignmentPacket packet(){
        ScalarAssignmentPacket p{};p.token=actor_lease;p.target=actor;p.owner=field_owner;
        p.kind=1;p.width=1;p.vtable=0x6e119b0;p.expected=1;p.value=0;
        p.boolean=0xff010001;p.flags=0x8001040010205ULL;p.offset=2288;
        std::memcpy(p.name,"CanBeInteractedWith",sizeof("CanBeInteractedWith"));return p;
    }
    bool original_dialogue_contract(){
        if(!call_identity(base,field_owner)||!call_is_class(base,field_owner.address)||
           !e33_mesh::named(base,field_owner.address,"BP_jRPG_NPC_Dialog_C","/Game/LevelTools/NPCs/BP_jRPG_NPC_Dialog")||
           !call_identity(base,available)||local_read<uint64_t>(available.address+32)!=field_owner.address||
           !exact_name(base,available.address+24,"IsInteractionAvailable")||
           !guard.original_dialogue_isolation_contract(actor,field_owner,available))return false;
        const auto p=packet();return scalar_request(p)&&scalar_property(base,p)!=0;
    }
    bool interaction_flag_enabled(){const auto p=packet();return scalar_read(p)!=0;}
    bool assign_interaction_false_once(){
        if(!owns_identity(owned_identity())||!original_dialogue_contract())return false;
        auto p=packet();assign_scalar(base,p);
        return !p.error&&p.outcome==CallDispatchReturned;
    }
};
}
