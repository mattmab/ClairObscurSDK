#pragma once
#include "npc_original_construction.h"
#include "npc_original_unregister.h"

namespace e33_npc_presentation {
struct RetirementBindings {
    CallIdentity interaction_system,unregister_nearby,unregister_distant;
    UnregisterJournal nearby{},distant{};
};
// One exact owned NPC, one persistent Lifecycle/ConstructionState/bindings set.
// The containing service must supply actual current-context/battle and measured
// assembly/cleanup guards. No boolean supplied over a wire grants those proofs.
template<class Pool,class Guard>
struct OriginalLifecycleOps : OriginalConstructionOps<Pool,Guard> {
    RetirementBindings& bindings;
    OriginalLifecycleOps(uint64_t base,ConstructionSource& source,ConstructionState& state,
            Pool& pool,Guard& guard,RetirementBindings& retirement):
        OriginalConstructionOps<Pool,Guard>{base,source,state,pool,guard},bindings(retirement){}
    bool unregister_owned_interactions_once(){
        auto idle=[&](){return this->current_context()&&this->battle_quiescent();};
        const auto& s=this->source;
        UnregisterContext context{s.controller,s.world,bindings.interaction_system,this->state.actor,
            s.actor_class,s.cdo,s.available,bindings.unregister_nearby,s.session,this->state.actor_lease};
        if(unregister_original(this->base,context,InteractionRegistry::Nearby,this->pool,idle,bindings.nearby)!=UnregisterResult::Complete)return false;
        context.function=bindings.unregister_distant;
        return unregister_original(this->base,context,InteractionRegistry::Distant,this->pool,idle,bindings.distant)==UnregisterResult::Complete;
    }
    bool verify_original_endplay_and_all_registrations_absent(){
        // Destruction can invalidate ordinary call_identity while the strong
        // lease still exists. The cleanup observer must use the durable exact
        // identity and prove original EndPlay, all five prompt/interaction
        // locations and constructed listeners/ID maps independently.
        return this->current_context()&&this->battle_quiescent()&&
            this->guard.verify_original_endplay_and_all_registrations_absent(this->state.actor);
    }
    bool release_owned_lease_once(){
        if(!this->current_context()||!this->battle_quiescent())return false;
        TargetStrongReferenceOps ops{this->base,{-1,0,0}};
        auto release=[&](uint64_t& lease){
            if(!lease)return true;
            if(this->pool.release(ops,this->source.session,lease)!=StrongLeaseResult::Ok)return false;
            lease=0;return true;
        };
        // The Lifecycle has already verified complete cleanup and journaled
        // ReleasePending. Any failure retains unresolved ownership, never
        // automatically retries release, and cannot start a replacement actor.
        return release(this->state.actor_lease)&&release(this->source.cdo_lease)&&release(this->source.class_lease);
    }
};
}
