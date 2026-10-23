#pragma once
#include "battle_parameter_frame.h"

namespace e33_enemy_spawn {
enum class BattleEntryState { Empty, DispatchUnknown, NotDispatched, Returned, CopyVerified, Retired };

// ProcessEvent returning is an acknowledgement of dispatch, not proof that an
// asynchronous battle started or ended. Parameter storage can retire after an
// independently verified engine-owned copy, or encounter retirement. Neither
// outcome retires the separately owned exploration actor. Never replay dispatch.
class BattleEntryTransaction {
    BattleEntryState state_=BattleEntryState::Empty;
public:
    BattleEntryState state()const{return state_;}
    bool quarantined()const{return state_==BattleEntryState::DispatchUnknown;}
    bool pending()const{return state_==BattleEntryState::DispatchUnknown||state_==BattleEntryState::Returned||state_==BattleEntryState::CopyVerified;}
    template<class Ops> bool dispatch(const void* parameters,Ops& ops) {
        if(state_!=BattleEntryState::Empty||!parameters||!ops.entry_preflight(parameters))return false;
        // Persist before calling any engine entry point, including SEH paths.
        state_=BattleEntryState::DispatchUnknown;
        const auto result=ops.invoke_entry(parameters);
        if(result==ParameterCall::NotDispatched){state_=BattleEntryState::NotDispatched;return false;}
        if(result!=ParameterCall::Completed)return false;
        state_=BattleEntryState::Returned;return true;
    }
    template<class Ops> bool confirm_owned_copy(const void* parameters,Ops& ops){
        if(state_!=BattleEntryState::Returned||!parameters||!ops.owned_parameter_copy_ready(parameters))return false;
        state_=BattleEntryState::CopyVerified;return true;
    }
    template<class Ops> bool retire(Ops& ops) {
        if(state_==BattleEntryState::Empty||state_==BattleEntryState::NotDispatched||state_==BattleEntryState::Retired)return true;
        if(state_==BattleEntryState::CopyVerified){state_=BattleEntryState::Retired;return true;}
        if(state_!=BattleEntryState::Returned||!ops.entry_retirement_ready())return false;
        state_=BattleEntryState::Retired;return true;
    }
};
}
