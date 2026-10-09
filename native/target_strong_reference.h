#pragma once
#include "strong_reference.h"
#include "session_protocol.h"
#include "fixed_invocation.h"
#include "reflected_invocation.h"

// The containing runtime verifies the exact executable before constructing this.
// Evidence: strong-holder-creation-body/paths and gc-guard-detail/name-bodies.
struct TargetStrongReferenceOps {
    uint64_t base;
    CallIdentity identity;
    uint64_t base_vtable() const { return base+0x6de2638; }
    uint64_t strong_vtable() const { return base+0x6eddd50; }
    bool can_release() const {
        return GetCurrentThreadId()==local_read<DWORD>(base+0x9272d30) &&
            !local_read<uint8_t>(base+0x9272cfc) &&
            !local_read<uint8_t>(base+0x934e968);
    }
    bool can_create(uint64_t object) const {
        return can_release() && !local_read<uint8_t>(base+0x9272cea) &&
            object==identity.address && call_identity(base,identity)==object &&
            !(local_read<uint32_t>(object+8)&0x40000000);
    }
    bool can_assign() const {
        return can_release() && !local_read<uint8_t>(base+0x9272cea);
    }
    CallIdentity capture(uint64_t object) const { return call_capture(base,object); }
    int32_t allocate_serial(int32_t index) const {
        // 1413c5c50 assembly: RCX=&GUObjectArray, EDX=object index, EAX=serial.
        // 1413ab8b0 owns the counter increment and item compare-exchange.
        return reinterpret_cast<int32_t(__fastcall*)(void*,int32_t)>(base+0x13ab8b0)
            (reinterpret_cast<void*>(base+0x9361b60),index);
    }
    TargetStrongReference* allocate() const {
        return reinterpret_cast<TargetStrongReference*(*)(size_t)>(base+0x4a98010)(24);
    }
    void register_holder(TargetStrongReference* holder) const {
        reinterpret_cast<void(*)(TargetStrongReference*)>(base+0x12514b0)(holder);
    }
    bool barrier_needed() const { return local_read<uint8_t>(base+0x934e968)!=0; }
    void write_barrier(uint64_t object) const {
        reinterpret_cast<void(*)(uint64_t)>(base+0x12b0e90)(object);
    }
    void destroy(TargetStrongReference* holder) const {
        reinterpret_cast<TargetStrongReference*(*)(TargetStrongReference*,uint32_t)>
            (base+0x1e6c4f0)(holder,1);
    }
};
