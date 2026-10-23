#pragma once
// Shared sequencing only. Consumers retain class admission, world/game-thread
// authority, exact engine profiles, actor/lease ownership and retirement policy.
// The journal must outlive dispatch and must only be reset after cleanup.
namespace e33_owned_actor {
enum class ConstructionPhase {
    Ready, AllocationPending, Allocated, IdentityPending, Identified,
    RetentionPending, Retained, PreparationPending, Prepared,
    ConstructionPending, Constructed, FinalizationPending, Complete
};
enum class ConstructionResult {
    Complete, AlreadyAttempted, AllocationFailed, IdentityFailed,
    RetentionFailed, PreparationFailed, ConstructionFailed, FinalizationFailed
};
struct ConstructionJournal {
    ConstructionPhase phase=ConstructionPhase::Ready;
    bool attempted=false;
};

// Before identify() captures an actor, an interrupted allocation cannot be
// proven retired by inspecting an empty actor/lease field.
inline bool allocation_unresolved(const ConstructionJournal& journal,bool captured_actor) {
    return journal.phase==ConstructionPhase::AllocationPending||journal.phase==ConstructionPhase::Allocated||
        (journal.phase==ConstructionPhase::IdentityPending&&!captured_actor);
}

// Every callback validates the exact identities/context appropriate to its
// operation. allocation() dispatches once; identify() immediately records the
// returned actor in the consumer's durable owner before retention or any other
// engine call. A false callback or exception leaves the journal pending at that
// boundary. Nothing rolls back, releases, destroys, or retries automatically.
template<class Allocate,class Identify,class Retain,class Prepare,class Finish,class Finalize>
ConstructionResult construct(ConstructionJournal& journal,Allocate allocate,
        Identify identify,Retain retain,Prepare prepare,Finish finish,Finalize finalize) {
    if(journal.attempted||journal.phase!=ConstructionPhase::Ready)
        return ConstructionResult::AlreadyAttempted;
    journal.attempted=true;
    journal.phase=ConstructionPhase::AllocationPending;
    if(!allocate())return ConstructionResult::AllocationFailed;
    journal.phase=ConstructionPhase::Allocated;
    journal.phase=ConstructionPhase::IdentityPending;
    if(!identify())return ConstructionResult::IdentityFailed;
    journal.phase=ConstructionPhase::Identified;
    journal.phase=ConstructionPhase::RetentionPending;
    if(!retain())return ConstructionResult::RetentionFailed;
    journal.phase=ConstructionPhase::Retained;
    journal.phase=ConstructionPhase::PreparationPending;
    if(!prepare())return ConstructionResult::PreparationFailed;
    journal.phase=ConstructionPhase::Prepared;
    journal.phase=ConstructionPhase::ConstructionPending;
    if(!finish())return ConstructionResult::ConstructionFailed;
    journal.phase=ConstructionPhase::Constructed;
    journal.phase=ConstructionPhase::FinalizationPending;
    if(!finalize())return ConstructionResult::FinalizationFailed;
    journal.phase=ConstructionPhase::Complete;
    return ConstructionResult::Complete;
}
}
