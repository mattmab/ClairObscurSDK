#pragma once
#include <cstdint>

enum class SlateReferenceState { Empty, Acquiring, Live, Releasing, Quarantined };
enum class SlateReferenceResult { Ok, Invalid, Busy, Deferred, Quarantined };
struct OwnedSlateReference {
    uint64_t widget=0, controller=0;
    SlateReferenceState state=SlateReferenceState::Empty;
    OwnedSlateReference()=default;
    OwnedSlateReference(const OwnedSlateReference&)=delete;
    OwnedSlateReference& operator=(const OwnedSlateReference&)=delete;
};

// Store in the pinned native session, never in client-owned mapping memory.
// Unknown atomic/destructor outcomes remain tracked and cannot be replayed.
template<class Ops>
SlateReferenceResult retain_slate_reference(Ops& ops,OwnedSlateReference& value,
                                           uint64_t widget,uint64_t controller) {
    if(value.state!=SlateReferenceState::Empty) return SlateReferenceResult::Busy;
    if(!widget || !controller || !ops.can_acquire(widget,controller)) return SlateReferenceResult::Invalid;
    value.widget=widget; value.controller=controller; value.state=SlateReferenceState::Acquiring;
    if(!ops.add_reference(controller)) {
        value.state=SlateReferenceState::Quarantined;
        return SlateReferenceResult::Quarantined;
    }
    value.state=SlateReferenceState::Live;
    return SlateReferenceResult::Ok;
}
template<class Ops>
SlateReferenceResult release_slate_reference(Ops& ops,OwnedSlateReference& value) {
    if(value.state==SlateReferenceState::Empty) return SlateReferenceResult::Ok;
    if(value.state!=SlateReferenceState::Live) {
        value.state=SlateReferenceState::Quarantined;
        return SlateReferenceResult::Quarantined;
    }
    if(!ops.can_release()) return SlateReferenceResult::Deferred;
    if(!ops.known_reference(value.widget,value.controller)) {
        value.state=SlateReferenceState::Quarantined;
        return SlateReferenceResult::Quarantined;
    }
    value.state=SlateReferenceState::Releasing;
    if(!ops.release_reference(value.controller)) {
        value.state=SlateReferenceState::Quarantined;
        return SlateReferenceResult::Quarantined;
    }
    value.widget=value.controller=0; value.state=SlateReferenceState::Empty;
    return SlateReferenceResult::Ok;
}
