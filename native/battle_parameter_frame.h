#pragma once
#include <array>
#include <cstdint>
#include <limits>

// Only FBattleStartParams (344 bytes, alignment 8) for the supported build.
// No wire codec and no engine entry point is exposed by this lifecycle helper.
// A persistent native owner must retain this frame and its source/struct leases
// until close is acknowledged. Unknown outcomes are quarantined, never replayed.
namespace e33_enemy_spawn {
inline bool parameter_destination_separate(uintptr_t destination,uint64_t source) {
    if(!destination||destination%8||destination>std::numeric_limits<uintptr_t>::max()-344||
       source>std::numeric_limits<uint64_t>::max()-392)return false;
    return destination+344<=source+48 || destination>=source+392;
}
enum class ParameterCall { NotDispatched, Completed, Unknown };
enum class ParameterFrameState { Empty, InitializeUnknown, Initialized,
    CopyUnknown, Copied, ArenaUnknown, ArenaBound, PolicyUnknown, PolicyApplied, DestroyUnknown, Closed };

class BattleParameterFrame {
    alignas(8) std::array<uint8_t,344> storage_{};
    ParameterFrameState state_=ParameterFrameState::Empty;
    bool attempted_=false;
    bool policy_attempted_=false;
    bool arena_attempted_=false;
public:
    BattleParameterFrame()=default;
    BattleParameterFrame(const BattleParameterFrame&)=delete;
    BattleParameterFrame& operator=(const BattleParameterFrame&)=delete;
    BattleParameterFrame(BattleParameterFrame&&)=delete;
    BattleParameterFrame& operator=(BattleParameterFrame&&)=delete;
    ParameterFrameState state()const{return state_;}
    bool attempted()const{return attempted_;}
    bool quarantined()const{return state_==ParameterFrameState::InitializeUnknown ||
        state_==ParameterFrameState::CopyUnknown || state_==ParameterFrameState::ArenaUnknown || state_==ParameterFrameState::PolicyUnknown || state_==ParameterFrameState::DestroyUnknown;}
    const void* copied_data()const{return state_==ParameterFrameState::Copied||state_==ParameterFrameState::ArenaBound||state_==ParameterFrameState::PolicyApplied?storage_.data():nullptr;}

    template<class Ops> bool bind_arena(Ops& ops){
        if(arena_attempted_||state_!=ParameterFrameState::Copied)return false;
        arena_attempted_=true;state_=ParameterFrameState::ArenaUnknown;
        const auto result=ops.bind(storage_.data());
        if(result==ParameterCall::NotDispatched){state_=ParameterFrameState::Copied;return false;}
        if(result!=ParameterCall::Completed)return false;
        state_=ParameterFrameState::ArenaBound;return true;
    }

    template<class Ops> bool apply_policy(Ops& ops) {
        if(policy_attempted_||(state_!=ParameterFrameState::Copied&&state_!=ParameterFrameState::ArenaBound))return false;
        const auto previous=state_;
        policy_attempted_=true;state_=ParameterFrameState::PolicyUnknown;
        const auto result=ops.apply(storage_.data());
        if(result==ParameterCall::NotDispatched){state_=previous;return false;}
        if(result!=ParameterCall::Completed)return false;
        state_=ParameterFrameState::PolicyApplied;return true;
    }

    template<class Ops> bool initialize_copy(Ops& ops) {
        if(attempted_ || state_!=ParameterFrameState::Empty || !ops.preflight())return false;
        attempted_=true;
        state_=ParameterFrameState::InitializeUnknown;
        const auto initialized=ops.initialize(storage_.data());
        if(initialized==ParameterCall::NotDispatched){state_=ParameterFrameState::Empty;return false;}
        if(initialized!=ParameterCall::Completed)return false;
        state_=ParameterFrameState::Initialized;
        // Revalidate source, retained identities and context after construction.
        if(!ops.preflight())return false;
        state_=ParameterFrameState::CopyUnknown;
        const auto copied=ops.copy(storage_.data());
        if(copied==ParameterCall::NotDispatched){state_=ParameterFrameState::Initialized;return false;}
        if(copied!=ParameterCall::Completed)return false;
        state_=ParameterFrameState::Copied;
        return true;
    }

    template<class Ops> bool close(Ops& ops) {
        if(state_==ParameterFrameState::Closed)return true;
        if(state_==ParameterFrameState::Empty){state_=ParameterFrameState::Closed;return true;}
        if(quarantined() || !ops.cleanup_ready())return false;
        const auto previous=state_;
        state_=ParameterFrameState::DestroyUnknown;
        const auto destroyed=ops.destroy(storage_.data());
        if(destroyed==ParameterCall::NotDispatched){state_=previous;return false;}
        if(destroyed!=ParameterCall::Completed)return false;
        state_=ParameterFrameState::Closed;
        return true;
    }
};
}
