#pragma once
#include <cstddef>
#include <cstdint>

namespace e33_trigger_anchor {
// Bounded, once-only retention for the original trigger's GI and five SCS
// components. A failed acquire can own quarantined storage without a token.
// Keep that uncertainty visible; neither capture nor release may replay it.
template<class Identity> struct RetainedTargets {
    Identity identities[8]{};
    uint64_t leases[8]{};
    size_t count=0;
    bool acquire_pending=false,release_pending=false,released=false;
    template<class Ops> bool add(Ops& ops,uint64_t object){
        if(acquire_pending||release_pending||released)return false;
        for(size_t i=0;i<count;++i)if(identities[i].address==object)
            return ops.exact_retained(identities[i],leases[i]);
        if(count>=8)return false;
        auto identity=ops.capture(object);
        if(!identity.address)return false;
        const auto slot=count++;
        identities[slot]=identity;
        acquire_pending=true;
        if(!ops.retain(identities[slot],leases[slot])||!leases[slot])return false;
        acquire_pending=false;
        return true;
    }
    template<class Ops> bool release(Ops& ops){
        if(released)return true;
        if(acquire_pending||release_pending)return false;
        release_pending=true;
        for(size_t i=0;i<count;++i){
            if(!leases[i]||!ops.release(leases[i]))return false;
            leases[i]=0;
        }
        release_pending=false;released=true;
        return true;
    }
};
}
