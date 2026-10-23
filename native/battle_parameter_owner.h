#pragma once
#include "battle_parameter_frame.h"
#include "battle_entry_transaction.h"

namespace e33_enemy_spawn {
enum class ParameterLeaseState { Empty, AcquireUnknown, Held, ReleaseUnknown, Released };
struct ParameterLease {uint64_t token=0;ParameterLeaseState state=ParameterLeaseState::Empty;};

// Persistent owner transaction. Ops must acquire NEW native-owner leases for
// root, struct and source (in that order); client tokens must never be adopted.
// The containing pinned runtime must keep this owner resident while pending(),
// including after SEH or an unknown acknowledgement, and close it before pools.
class BattleParameterOwner {
    BattleParameterFrame frame_;
    BattleEntryTransaction entry_;
    ParameterLease leases_[3]{};
    bool attempted_=false;
public:
    BattleParameterOwner()=default;
    BattleParameterOwner(const BattleParameterOwner&)=delete;
    BattleParameterOwner& operator=(const BattleParameterOwner&)=delete;
    bool attempted()const{return attempted_;}
    const ParameterLease& lease(unsigned index)const{return leases_[index];}
    const void* copied_data()const{return frame_.copied_data();}
    ParameterFrameState frame_state()const{return frame_.state();}
    BattleEntryState entry_state()const{return entry_.state();}
    bool pending()const {
        if(entry_.pending())return true;
        if(frame_.state()!=ParameterFrameState::Empty&&frame_.state()!=ParameterFrameState::Closed)return true;
        for(const auto& lease:leases_)
            if(lease.state!=ParameterLeaseState::Empty&&lease.state!=ParameterLeaseState::Released)return true;
        return false;
    }
    bool quarantined()const {
        if(frame_.quarantined()||entry_.quarantined())return true;
        for(const auto& lease:leases_)
            if(lease.state==ParameterLeaseState::AcquireUnknown||lease.state==ParameterLeaseState::ReleaseUnknown)return true;
        return false;
    }
    template<class Ops> bool apply_policy(Ops& ops) {
        for(const auto& lease:leases_)if(lease.state!=ParameterLeaseState::Held)return false;
        return frame_.apply_policy(ops);
    }
    template<class Ops> bool bind_arena(Ops& ops){
        for(const auto& lease:leases_)if(lease.state!=ParameterLeaseState::Held)return false;
        return frame_.bind_arena(ops);
    }
    template<class Ops> bool dispatch_entry(Ops& ops) {
        if(frame_.state()!=ParameterFrameState::PolicyApplied||quarantined())return false;
        for(const auto& lease:leases_)if(lease.state!=ParameterLeaseState::Held)return false;
        return entry_.dispatch(frame_.copied_data(),ops);
    }
    template<class Ops> bool confirm_entry_copy(Ops& ops){
        if(frame_.state()!=ParameterFrameState::PolicyApplied||quarantined())return false;
        for(const auto& lease:leases_)if(lease.state!=ParameterLeaseState::Held)return false;
        return entry_.confirm_owned_copy(frame_.copied_data(),ops);
    }
    template<class Ops> bool open(Ops& ops) {
        if(attempted_||pending()||frame_.state()!=ParameterFrameState::Empty||!ops.admit())return false;
        attempted_=true;
        for(unsigned index=0;index<3;++index){
            auto& lease=leases_[index];lease.state=ParameterLeaseState::AcquireUnknown;
            const auto result=ops.acquire(index,lease.token);
            if(result==ParameterCall::NotDispatched){
                // A supposedly undispatched acquisition publishing a token is
                // inconsistent: quarantine it instead of dropping ownership.
                if(!lease.token)lease.state=ParameterLeaseState::Empty;
                return false;
            }
            if(result!=ParameterCall::Completed||!lease.token)return false;
            lease.state=ParameterLeaseState::Held;
        }
        auto frame_ops=ops.frame_ops(leases_);
        return frame_.initialize_copy(frame_ops);
    }
    template<class Ops> bool close(Ops& ops) {
        // Neither an idle manager before asynchronous startup nor a returned
        // engine call proves retirement. An unknown call cannot be retired.
        if(!entry_.retire(ops))return false;
        // Source and struct leases remain held through frame destruction.
        auto frame_ops=ops.frame_ops(leases_);
        if(!frame_.close(frame_ops)||quarantined())return false;
        if(!pending())return true;
        if(!ops.release_ready())return false;
        for(unsigned index=3;index>0;--index){
            auto& lease=leases_[index-1];
            if(lease.state==ParameterLeaseState::Empty||lease.state==ParameterLeaseState::Released)continue;
            if(lease.state!=ParameterLeaseState::Held)return false;
            lease.state=ParameterLeaseState::ReleaseUnknown;
            const auto result=ops.release(index-1,lease.token);
            if(result==ParameterCall::NotDispatched){lease.state=ParameterLeaseState::Held;return false;}
            if(result!=ParameterCall::Completed)return false;
            lease.state=ParameterLeaseState::Released;
        }
        return true;
    }
};
}
