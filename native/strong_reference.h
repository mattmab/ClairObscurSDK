#pragma once
#include <cstddef>
#include <cstdint>

// Target-derived layout, not a public handle or a stock UE header. See
// research/WIDGET_OWNERSHIP.md. Storage must survive until explicit GT release.
struct TargetStrongReference {
    uint64_t vtable;
    uint8_t conditional;
    uint8_t registered;
    uint8_t padding[6];
    uint64_t object;
};
static_assert(sizeof(TargetStrongReference)==24);
static_assert(offsetof(TargetStrongReference,registered)==9);
static_assert(offsetof(TargetStrongReference,object)==16);

struct StrongReferenceStorage {
    TargetStrongReference* pointer=nullptr;
    bool registration_uncertain=false;
    bool destruction_uncertain=false;
};

enum class StrongReferenceResult {
    Ok, Occupied, InvalidContext, AllocationFailed, RegistrationRejected,
    ReleaseDeferred, ForeignHolder, RegistrationUncertain, DestructionUncertain
};

template<class Ops>
void destroy_strong_reference(Ops& ops, StrongReferenceStorage& storage) {
    // A destructor fault can happen after freeing. Preserve uncertainty rather
    // than dereferencing/retrying a pointer that may already be invalid.
    storage.destruction_uncertain=true;
    ops.destroy(storage.pointer);
    storage.pointer=nullptr;
    storage.destruction_uncertain=false;
}

// Ops supplies verified engine operations and identity/thread/GC guards.
// No automatic destructor: C++ scope exit may occur on the wrong thread.
// The caller must keep storage in the native session before any operation that
// can fault. Registration faults quarantine the allocation: its membership may
// have changed before the registered flag was set. Never free/retry blindly.
template<class Ops>
StrongReferenceResult create_strong_reference(Ops& ops, uint64_t object,
                                             StrongReferenceStorage& storage) {
    auto& owned=storage.pointer;
    if(storage.registration_uncertain) return StrongReferenceResult::RegistrationUncertain;
    if(storage.destruction_uncertain) return StrongReferenceResult::DestructionUncertain;
    if(owned) return StrongReferenceResult::Occupied;
    if(!object || !ops.can_create(object)) return StrongReferenceResult::InvalidContext;
    owned=ops.allocate();
    if(!owned) return StrongReferenceResult::AllocationFailed;
    *owned={};
    // Register inspects the flags/list membership, not the vtable or object.
    // Publish a complete native collector before registration, so an interrupted
    // registration cannot leave a pure-virtual base holder in the engine list.
    owned->vtable=ops.strong_vtable();
    owned->object=object;
    // Allocation can invalidate a previously observed identity/context.
    if(!ops.can_create(object)) {
        // Unregistered allocation has no GC-list membership. Destruction is
        // the target's own 24-byte deleting destructor, not a CRT free.
        destroy_strong_reference(ops,storage);
        return StrongReferenceResult::InvalidContext;
    }
    storage.registration_uncertain=true;
    ops.register_holder(owned);
    storage.registration_uncertain=false;
    if(!owned->registered) {
        destroy_strong_reference(ops,storage);
        return StrongReferenceResult::RegistrationRejected;
    }
    if(ops.barrier_needed()) ops.write_barrier(object);
    return StrongReferenceResult::Ok;
}

template<class Ops>
StrongReferenceResult release_strong_reference(Ops& ops, StrongReferenceStorage& storage) {
    auto& owned=storage.pointer;
    if(storage.registration_uncertain) return StrongReferenceResult::RegistrationUncertain;
    if(storage.destruction_uncertain) return StrongReferenceResult::DestructionUncertain;
    if(!owned) return StrongReferenceResult::Ok;
    if(!ops.can_release()) return StrongReferenceResult::ReleaseDeferred;
    if(owned->vtable!=ops.strong_vtable() && owned->vtable!=ops.base_vtable())
        return StrongReferenceResult::ForeignHolder;
    destroy_strong_reference(ops,storage);
    return StrongReferenceResult::Ok;
}
