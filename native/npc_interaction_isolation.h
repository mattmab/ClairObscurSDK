#pragma once
#include <cstdint>
namespace e33_npc_presentation {
struct InteractionIsolationIdentity {int32_t index=-1,serial=0;uint64_t address=0;};
enum class InteractionIsolationResult {Complete,Rejected,AlreadyAttempted,UnknownOutcome};
struct InteractionIsolationJournal {
    InteractionIsolationIdentity actor{};
    bool attempted=false,verified=false;
};
// Sequencing around the existing scalar assignment, not a new write primitive.
// Ops must prove game-thread context, exact owned identity/lease, the complete
// inherited availability body and typed field schema before any mutation.
template<class Ops> bool interaction_isolation_held(Ops& ops,const InteractionIsolationJournal& journal){
    return journal.attempted&&journal.verified&&ops.owns_identity(journal.actor)&&
        ops.original_dialogue_contract()&&!ops.interaction_flag_enabled();
}
template<class Ops> InteractionIsolationResult isolate_owned_interaction(Ops& ops,InteractionIsolationJournal& journal){
    if(journal.attempted)return InteractionIsolationResult::AlreadyAttempted;
    const auto actor=ops.owned_identity();
    if(actor.index<0||actor.serial<=0||actor.address<0x10000||!ops.owns_identity(actor)||
       !ops.original_dialogue_contract()||!ops.interaction_flag_enabled())return InteractionIsolationResult::Rejected;
    journal.actor=actor;journal.attempted=true;
    if(!ops.assign_interaction_false_once()||!ops.owns_identity(actor)||
       !ops.original_dialogue_contract()||ops.interaction_flag_enabled())return InteractionIsolationResult::UnknownOutcome;
    journal.verified=true;return InteractionIsolationResult::Complete;
}
}
