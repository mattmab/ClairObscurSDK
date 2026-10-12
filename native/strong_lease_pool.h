#pragma once
#include "strong_reference.h"
#include <array>
#include <limits>
#include <thread>
#include "lease_blocks.h"

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
#ifdef E33_GROWING_LEASE_SESSION
constexpr size_t kDefaultLeaseMaximum=4096;
#elif defined(E33_WIDGET_CAPACITY_SESSION)
constexpr size_t kDefaultLeaseMaximum=256;
#else
constexpr size_t kDefaultLeaseMaximum=128;
#endif
template<size_t Capacity=128,size_t Maximum=(Capacity==128 ? kDefaultLeaseMaximum : Capacity)>
class StrongLeasePool {
    struct Entry { uint64_t token=0,owner=0; StrongReferenceStorage storage{}; };
    LeaseBlocks<Entry,Capacity,Maximum> entries_;
    uint64_t session_=0, next_=1;
    uint64_t current_owner_=0;
    uint32_t limit_=uint32_t(Maximum),quota_=uint32_t(Maximum),reserve_=0,peak_=0;
    bool closing_=false;
    std::thread::id thread_{};
    struct OwnerPeak { uint64_t owner=0;uint32_t peak=0;bool used=false; };
    std::array<OwnerPeak,64> owners_{};
    bool on_thread() const { return thread_==std::this_thread::get_id(); }
    uint32_t owner_active(uint64_t owner) const {
        uint32_t count=0;for(const auto& entry:entries_) if(entry.token && entry.owner==owner) ++count;return count;
    }
    OwnerPeak* owner_record(uint64_t owner,bool create) {
        for(auto& record:owners_) if(record.used && record.owner==owner) return &record;
        if(create) for(auto& record:owners_) if(!record.used) { record={owner,0,true};return &record; }
        return nullptr;
    }
public:
    static constexpr uint32_t maximum=uint32_t(Maximum);
    uint32_t limit() const { return limit_; }
    uint32_t capacity() const { return uint32_t(entries_.capacity()); }
    uint32_t peak() const { return peak_; }
    size_t storage_bytes() const { return sizeof(*this)+entries_.bytes()-Capacity*sizeof(Entry); }
    uint32_t quota() const { return quota_; }
    uint32_t reserve() const { return reserve_; }
    bool configure(uint32_t limit,uint32_t quota,uint32_t reserve) {
        if(!on_thread() || active() || closing_ || !session_ || limit<Capacity || limit>Maximum ||
           !quota || quota>limit || reserve>=limit) return false;
        limit_=limit;quota_=quota;reserve_=reserve;return true;
    }
    bool set_owner(uint64_t session,uint64_t owner) {
        if(!on_thread() || !owns(session)) return false;
        current_owner_=owner;return true;
    }
    template<class Visitor> void owner_statistics(Visitor&& visitor) const {
        for(const auto& record:owners_) if(record.used) visitor(record.owner,owner_active(record.owner),record.peak);
    }
    uint32_t active() const {
        uint32_t count=0;
        for(const auto& e: entries_) if(e.token) ++count;
        return count;
    }
    bool owns(uint64_t session) const { return session && session==session_; }
    bool owns_object(uint64_t session,uint64_t token,uint64_t object) const {
        if(!owns(session) || !token || !object) return false;
        for(const auto& e:entries_) if(e.token==token) {
            const auto& s=e.storage;
            return s.pointer && !s.registration_uncertain && !s.destruction_uncertain &&
                s.pointer->registered && s.pointer->object==object;
        }
        return false;
    }
    StrongLeaseResult preflight(uint64_t session,uint32_t count) {
        if(!on_thread()) return StrongLeaseResult::InvalidContext;
        if(!owns(session)) return StrongLeaseResult::SessionMismatch;
        if(closing_) return StrongLeaseResult::Busy;
        const auto used=active();
        if(used>limit_ || count>limit_-used) return StrongLeaseResult::Capacity;
        if(count && current_owner_ && (owner_active(current_owner_)>quota_ || count>quota_-owner_active(current_owner_) ||
            used>limit_-reserve_ || count>limit_-reserve_-used)) return StrongLeaseResult::Capacity;
        if(count && !owner_record(current_owner_,false)) {
            bool room=false;for(const auto& record:owners_) if(!record.used) room=true;
            if(!room) return StrongLeaseResult::Capacity;
        }
        if(uint64_t(count)>std::numeric_limits<uint64_t>::max()-next_)
            return StrongLeaseResult::Exhausted;
        // Reserve storage before a retained engine call, so growth cannot
        // invalidate its admission after it has already constructed objects.
        if(!entries_.reserve(used+count)) return StrongLeaseResult::AllocationFailed;
        return StrongLeaseResult::Ok;
    }
    StrongLeaseResult begin(uint64_t session) {
        if(!session) return StrongLeaseResult::SessionMismatch;
        if(session_ || active()) return StrongLeaseResult::Busy;
        thread_=std::this_thread::get_id();session_=session;current_owner_=0;
        peak_=0;owners_={};closing_=false;owner_record(0,true);return StrongLeaseResult::Ok;
    }
    template<class Ops>
    StrongLeaseResult acquire(Ops& ops,uint64_t session,uint64_t object,uint64_t& token) {
        token=0;
        const auto allowed=preflight(session,1);
        if(allowed!=StrongLeaseResult::Ok) return allowed;
        for(auto& e:entries_) {
            if(e.token) continue;
            const auto before=active();auto* accounting=owner_record(current_owner_,true);
            if(!accounting) return StrongLeaseResult::Capacity;
            const auto owner_before=owner_active(current_owner_);
            e.owner=current_owner_;e.token=next_++;
            if(peak_<before+1) peak_=before+1;
            if(accounting->peak<owner_before+1) accounting->peak=owner_before+1;
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
        if(!on_thread()) return StrongLeaseResult::InvalidContext;
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
        if(!on_thread()) return StrongLeaseResult::InvalidContext;
        if(!owns(session)) return StrongLeaseResult::SessionMismatch;
        closing_=true; // No reentrant acquisitions during teardown.
        StrongLeaseResult overall=StrongLeaseResult::Ok;
        for(auto& e:entries_) {
            if(!e.token) continue;
            auto result=lease_result(release_strong_reference(ops,e.storage));
            if(result==StrongLeaseResult::Ok) e={};
            else if(overall==StrongLeaseResult::Ok || overall==StrongLeaseResult::Deferred) overall=result;
        }
        if(!active()) { session_=0;closing_=false;current_owner_=0; }
        return overall;
    }
};
