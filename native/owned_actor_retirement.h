#pragma once
// Shared sequencing only. Each consumer supplies exact admission, ownership,
// engine operations and cleanup observations; this helper grants none.
// Keep the phase durable across dispatch. Pending effects are never replayed.
namespace e33_owned_actor {
enum class RetirementPhase { Ready, UnregisterPending, Unregistered, DestroyPending, Destroyed,
    CleanupVerified, ReleasePending, Complete };
enum class RetirementResult { Complete, Deferred, UnknownOutcome };

template<class Ops> RetirementResult retire(RetirementPhase& retirement,
        bool construction_attempted,Ops& ops){
    if(retirement==RetirementPhase::Complete)return RetirementResult::Complete;
    if(retirement==RetirementPhase::UnregisterPending||retirement==RetirementPhase::DestroyPending||retirement==RetirementPhase::ReleasePending)
        return RetirementResult::UnknownOutcome;
    if(!construction_attempted){retirement=RetirementPhase::Complete;return RetirementResult::Complete;}
    if(!ops.current_context()||!ops.battle_quiescent())return RetirementResult::Deferred;
    if(retirement==RetirementPhase::Ready){
        if(!ops.exact_owned_actor())return RetirementResult::Deferred;
        retirement=RetirementPhase::UnregisterPending;
        // Only original unregister functions for this exact owned actor;
        // never clear game arrays, prompts or unrelated listeners.
        if(!ops.unregister_owned_interactions_once())return RetirementResult::UnknownOutcome;
        retirement=RetirementPhase::Unregistered;
    }
    if(retirement==RetirementPhase::Unregistered){
        if(!ops.exact_owned_actor())return RetirementResult::Deferred;
        retirement=RetirementPhase::DestroyPending;
        if(!ops.destroy_owned_actor_once())return RetirementResult::UnknownOutcome;
        retirement=RetirementPhase::Destroyed;
    }
    if(retirement==RetirementPhase::Destroyed){
        // Pure observations can be retried as EndPlay settles. Retain the
        // lease and durable actor identity until every cleanup gate passes.
        if(!ops.verify_original_endplay_and_all_registrations_absent())return RetirementResult::Deferred;
        retirement=RetirementPhase::CleanupVerified;
    }
    if(retirement==RetirementPhase::CleanupVerified){
        retirement=RetirementPhase::ReleasePending;
        if(!ops.release_owned_lease_once())return RetirementResult::UnknownOutcome;
        retirement=RetirementPhase::Complete;
    }
    return RetirementResult::Complete;
}
}
