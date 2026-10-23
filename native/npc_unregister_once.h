#pragma once
namespace e33_npc_presentation {
enum class UnregisterPhase { Ready, Pending, Complete };
enum class UnregisterResult { Complete, Rejected, UnknownOutcome };
// Keep one journal for each original unregister function. A failed validation
// is retryable; any dispatched call (including an exception) is never replayed.
struct UnregisterJournal {
    UnregisterPhase phase=UnregisterPhase::Ready;
    template<class Ops> UnregisterResult run(Ops& ops){
        if(phase==UnregisterPhase::Complete)return UnregisterResult::Complete;
        if(phase==UnregisterPhase::Pending)return UnregisterResult::UnknownOutcome;
        if(!ops.validate())return UnregisterResult::Rejected;
        phase=UnregisterPhase::Pending;
        if(!ops.dispatch_once())return UnregisterResult::UnknownOutcome;
        phase=UnregisterPhase::Complete;
        return UnregisterResult::Complete;
    }
};
}
