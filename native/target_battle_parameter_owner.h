#pragma once
#include "battle_parameter_owner.h"
#include "target_battle_parameter_frame.h"
#include "target_strong_reference.h"
#include "strong_lease_pool.h"
#include "stable_identity.h"

namespace e33_enemy_spawn {
template<class Pool> struct TargetBattleParameterOwnerOps {
    TargetBattleParameterOps<Pool> engine;
    // No production dispatch is exposed yet. Copy-only research cannot assert
    // encounter retirement; the eventual entry owner must supply exact proof.
    bool entry_retirement_ready()const{return false;}
    bool admit() {
        return engine.source_profile_ready()&&engine.leases.preflight(engine.session,3)==StrongLeaseResult::Ok;
    }
    CallIdentity& identity(unsigned index) {
        return index==0?engine.root:(index==1?engine.structure:engine.source);
    }
    ParameterCall acquire(unsigned index,uint64_t& token) {
        if(index>=3)return ParameterCall::NotDispatched;
        return acquire_identity(identity(index),token);
    }
    ParameterCall acquire_identity(CallIdentity& id,uint64_t& token) {
        if(token||!engine.source_profile_ready()||!engine.valid(id))return ParameterCall::NotDispatched;
        TargetStrongReferenceOps refs{engine.base,id};
        const auto allowed=engine.leases.preflight(engine.session,1);
        if(allowed!=StrongLeaseResult::Ok)return ParameterCall::NotDispatched;
        const auto result=engine.leases.acquire(refs,engine.session,id.address,token);
        if(result!=StrongLeaseResult::Ok) {
            // Allocator/registration failures are conservative: the pool may
            // have published internal uncertainty even without a returned token.
            return ParameterCall::Unknown;
        }
        if(!token||!stabilize_retained_identity(refs,id))return ParameterCall::Unknown;
        return ParameterCall::Completed;
    }
    TargetBattleParameterOps<Pool> frame_ops(const ParameterLease (&leases)[3]) {
        auto result=engine;
        result.root_lease=leases[0].token;
        result.struct_lease=leases[1].token;
        result.source_lease=leases[2].token;
        return result;
    }
    bool release_ready()const {
        return TargetStrongReferenceOps{engine.base,{}}.can_release();
    }
    ParameterCall release(unsigned index,uint64_t token) {
        if(index>=3)return ParameterCall::NotDispatched;
        return release_token(token);
    }
    ParameterCall release_token(uint64_t token) {
        if(!token||!release_ready())return ParameterCall::NotDispatched;
        TargetStrongReferenceOps refs{engine.base,{}};
        const auto result=engine.leases.release(refs,engine.session,token);
        if(result==StrongLeaseResult::Ok)return ParameterCall::Completed;
        if(result==StrongLeaseResult::Deferred||result==StrongLeaseResult::InvalidContext)
            return ParameterCall::NotDispatched;
        return ParameterCall::Unknown;
    }
};
}
