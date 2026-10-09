#pragma once
#include "strong_reference.h"
#include <array>
#include <limits>

enum class StrongLeaseResult : uint32_t {
    Ok=0, SessionMismatch=400, Capacity=401, Stale=402, Busy=403,
    InvalidContext=404, AllocationFailed=405, RegistrationRejected=406,
    Deferred=407, Quarantined=408, ForeignHolder=409, Exhausted=410
};
inline StrongLeaseResult lease_result(StrongReferenceResult result) {
    switch(result) {
    case StrongReferenceResult::Ok: return StrongLeaseResult::Ok;
    case StrongReferenceResult::InvalidContext: return StrongLeaseResult::InvalidContext;
    case StrongReferenceResult::AllocationFailed: return StrongLeaseResult::AllocationFailed;
    case StrongReferenceResult::RegistrationRejected: return StrongLeaseResult::RegistrationRejected;
    case StrongReferenceResult::ReleaseDeferred: return StrongLeaseResult::Deferred;
    case StrongReferenceResult::RegistrationUncertain:
    case StrongReferenceResult::DestructionUncertain: return StrongLeaseResult::Quarantined;
    case StrongReferenceResult::ForeignHolder: return StrongLeaseResult::ForeignHolder;
    default: return StrongLeaseResult::Busy;
    }
}

// Owned by the pinned runtime, used only on its game thread. Tokens are opaque,
// monotonic across sessions and never recycled even if a creation fails.
template<size_t Capacity=128>
class StrongLeasePool {
    struct Entry { uint64_t token=0; StrongReferenceStorage storage{}; };
    std::array<Entry,Capacity> entries_{};
    uint64_t session_=0, next_=1;
public:
    uint32_t active() const {
        uint32_t count=0;
        for(const auto& e: entries_) if(e.token) ++count;
        return count;
    }
    bool owns(uint64_t session) const { return session && session==session_; }
    StrongLeaseResult preflight(uint64_t session,uint32_t count) const {
        if(!owns(session)) return StrongLeaseResult::SessionMismatch;
        if(count>Capacity-active()) return StrongLeaseResult::Capacity;
        if(uint64_t(count)>std::numeric_limits<uint64_t>::max()-next_)
            return StrongLeaseResult::Exhausted;
        return StrongLeaseResult::Ok;
    }
    StrongLeaseResult begin(uint64_t session) {
        if(!session) return StrongLeaseResult::SessionMismatch;
        if(session_ || active()) return StrongLeaseResult::Busy;
        session_=session; return StrongLeaseResult::Ok;
    }
    template<class Ops>
    StrongLeaseResult acquire(Ops& ops,uint64_t session,uint64_t object,uint64_t& token) {
        token=0;
        if(!owns(session)) return StrongLeaseResult::SessionMismatch;
        if(next_==std::numeric_limits<uint64_t>::max()) return StrongLeaseResult::Exhausted;
        for(auto& e:entries_) {
            if(e.token) continue;
            e.token=next_++;
            // Entry is published before any engine allocation/registration.
            // If an outer SEH boundary catches a fault, close can still see it.
            auto result=lease_result(create_strong_reference(ops,object,e.storage));
            if(result==StrongLeaseResult::Ok) token=e.token;
            else if(!e.storage.pointer && !e.storage.destruction_uncertain &&
                    !e.storage.registration_uncertain) e={};
            return result;
        }
        return StrongLeaseResult::Capacity;
    }
    template<class Ops>
    StrongLeaseResult release(Ops& ops,uint64_t session,uint64_t token) {
        if(!owns(session)) return StrongLeaseResult::SessionMismatch;
        if(!token) return StrongLeaseResult::Stale;
        for(auto& e:entries_) {
            if(e.token!=token) continue;
            auto result=lease_result(release_strong_reference(ops,e.storage));
            if(result==StrongLeaseResult::Ok) e={};
            return result;
        }
        return StrongLeaseResult::Stale;
    }
    template<class Ops>
    StrongLeaseResult close(Ops& ops,uint64_t session) {
        if(!owns(session)) return StrongLeaseResult::SessionMismatch;
        StrongLeaseResult overall=StrongLeaseResult::Ok;
        for(auto& e:entries_) {
            if(!e.token) continue;
            auto result=lease_result(release_strong_reference(ops,e.storage));
            if(result==StrongLeaseResult::Ok) e={};
            else if(overall==StrongLeaseResult::Ok || overall==StrongLeaseResult::Deferred) overall=result;
        }
        if(!active()) session_=0;
        return overall;
    }
};
