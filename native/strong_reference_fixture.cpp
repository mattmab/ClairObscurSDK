#include "strong_reference.h"
#include <cstdio>
#include <stdexcept>
#include <string>

static void require(bool pass,const char* message) {
    if(!pass) throw std::runtime_error(message);
}
struct FakeEngine {
    TargetStrongReference storage{};
    bool allowed=true, release_allowed=true, allocation=true, registration=true;
    bool barrier=false, invalidate_after_allocation=false, fault_after_registration=false;
    bool freed=false;
    bool fault_after_free=false;
    std::string events;
    uint64_t base_vtable() const { return 0x100; }
    uint64_t strong_vtable() const { return 0x200; }
    bool can_create(uint64_t object) const { return allowed && object==0x1234; }
    bool can_release() const { return release_allowed; }
    TargetStrongReference* allocate() {
        events+='A';
        if(invalidate_after_allocation) allowed=false;
        return allocation ? &storage : nullptr;
    }
    void register_holder(TargetStrongReference* h) {
        require(h->vtable==strong_vtable() && !h->registered && !h->conditional && h->object==0x1234,
                "registration receives complete native collector");
        events+='R'; h->registered=registration;
        if(fault_after_registration) throw std::runtime_error("injected native fault");
    }
    bool barrier_needed() const { return barrier; }
    void write_barrier(uint64_t object) {
        require(storage.object==object && storage.registered && storage.vtable==strong_vtable(),
                "barrier follows registration and assignment");
        events+='B';
    }
    void destroy(TargetStrongReference* h) {
        require(h==&storage && !freed,"no foreign free or double destroy");
        events+=h->registered ? "UF" : "F";
        h->registered=0; freed=true;
        if(fault_after_free) throw std::runtime_error("injected destructor fault");
    }
};
int main() {
    using R=StrongReferenceResult;
    {
        FakeEngine e; StrongReferenceStorage h;
        require(create_strong_reference(e,0x1234,h)==R::Ok && h.pointer->object==0x1234,"create");
        require(create_strong_reference(e,0x1234,h)==R::Occupied,"no overwrite");
        e.release_allowed=false;
        require(release_strong_reference(e,h)==R::ReleaseDeferred && h.pointer && !e.freed,"defer on wrong context");
        e.release_allowed=true;
        require(release_strong_reference(e,h)==R::Ok && !h.pointer && e.events=="ARUF","unregister before free");
        require(release_strong_reference(e,h)==R::Ok && e.events=="ARUF","idempotent empty release");
    }
    {
        FakeEngine e; e.barrier=true; StrongReferenceStorage h;
        require(create_strong_reference(e,0x1234,h)==R::Ok && e.events=="ARB","conditional barrier");
        h.pointer->vtable=0x300;
        require(release_strong_reference(e,h)==R::ForeignHolder && h.pointer && !e.freed,"foreign holder rejected");
    }
    {
        FakeEngine e; e.registration=false; StrongReferenceStorage h;
        require(create_strong_reference(e,0x1234,h)==R::RegistrationRejected && !h.pointer && e.events=="ARF",
                "registration rejection releases only unregistered allocation");
    }
    {
        FakeEngine e; e.invalidate_after_allocation=true; StrongReferenceStorage h;
        require(create_strong_reference(e,0x1234,h)==R::InvalidContext && !h.pointer && e.events=="AF",
                "identity/context revalidated after allocation");
    }
    {
        FakeEngine e; e.allocation=false; StrongReferenceStorage h;
        require(create_strong_reference(e,0x1234,h)==R::AllocationFailed && !h.pointer && e.events=="A","allocation failure");
        e.events.clear(); e.allowed=false;
        require(create_strong_reference(e,0x1234,h)==R::InvalidContext && e.events.empty(),"preflight rejection");
    }
    {
        FakeEngine e; e.fault_after_registration=true; StrongReferenceStorage h;
        try { create_strong_reference(e,0x1234,h); } catch(const std::runtime_error&) {}
        require(h.pointer && h.pointer->registered && !e.freed,"fault retains tracked storage");
        require(release_strong_reference(e,h)==R::RegistrationUncertain && h.pointer && !e.freed && e.events=="AR",
                "ambiguous registration quarantined without free");
    }
    {
        FakeEngine e; StrongReferenceStorage h;
        require(create_strong_reference(e,0x1234,h)==R::Ok,"prepare destructor fault");
        e.fault_after_free=true;
        try { release_strong_reference(e,h); } catch(const std::runtime_error&) {}
        require(e.freed && h.destruction_uncertain,"track destructor uncertainty");
        require(release_strong_reference(e,h)==R::DestructionUncertain && e.events=="ARUF","no destructor retry");
        require(create_strong_reference(e,0x1234,h)==R::DestructionUncertain,"no reuse after uncertain free");
    }
    std::puts("Strong-reference fixture: creation, barrier, rejection, deferred release and fault quarantine passed.");
}
