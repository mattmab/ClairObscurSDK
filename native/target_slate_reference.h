#pragma once
#include "owned_slate_reference.h"
#include "target_strong_reference.h"
#include <climits>

// Exact Steam23765773 only; caller verifies executable fingerprint first.
// Allocation3228a00 and release paths3709d70/1603dc0 establish the layout.
// Live vtable740a750 resolves to destructors322bc20 and161dae0.
struct TargetViewportReferenceProfile {
    static constexpr uint64_t controller_vtable=0x740a750, widget_vtable=0x6e78128;
    static constexpr uint64_t destroy_object=0x322bc20, destroy_controller=0x161dae0;
};
// SButton allocation1610f90: 0x398 bytes, embedded widget+0x10, counts+8/+c.
// Controller functions1632a80/161d960 corroborate final destruction and free.
struct TargetButtonReferenceProfile {
    static constexpr uint64_t controller_vtable=0x6e65f20, widget_vtable=0x6e6e7e0;
    static constexpr uint64_t destroy_object=0x1632a80, destroy_controller=0x161d960;
};
template<class Profile>
struct VerifiedSlateReferenceOps {
    uint64_t base;
    bool can_release() const {
        return GetCurrentThreadId()==local_read<DWORD>(base+0x9272d30) &&
            !local_read<uint8_t>(base+0x9272cea) &&
            !local_read<uint8_t>(base+0x9272cfc) &&
            !local_read<uint8_t>(base+0x934e968);
    }
    bool known_reference(uint64_t widget,uint64_t controller) const {
        if(!widget || controller<0x10000 || widget!=controller+0x10 ||
           local_read<uint64_t>(controller)!=base+Profile::controller_vtable ||
           local_read<uint64_t>(base+Profile::controller_vtable)!=base+Profile::destroy_object ||
           local_read<uint64_t>(base+Profile::controller_vtable+8)!=base+Profile::destroy_controller ||
           local_read<uint64_t>(widget)!=base+Profile::widget_vtable) return false;
        auto strong=local_read<LONG>(controller+8), weak=local_read<LONG>(controller+12);
        return strong>0 && strong<LONG_MAX && weak>0 && weak<LONG_MAX;
    }
    bool can_acquire(uint64_t widget,uint64_t controller) const {
        return can_release() && known_reference(widget,controller);
    }
    bool add_reference(uint64_t controller) const {
        // The engine's current shared owner must be verified by the caller on
        // this game thread. CAS refuses resurrection from zero or overflow.
        auto* strong=reinterpret_cast<volatile LONG*>(controller+8);
        auto observed=*strong;
        while(observed>0 && observed<LONG_MAX) {
            auto prior=InterlockedCompareExchange(strong,observed+1,observed);
            if(prior==observed) return true;
            observed=prior;
        }
        return false;
    }
    bool release_reference(uint64_t controller) const {
        auto remaining=InterlockedDecrement(reinterpret_cast<volatile LONG*>(controller+8));
        if(remaining<0) return false;
        if(remaining==0) {
            reinterpret_cast<void(__fastcall*)(void*)>(base+Profile::destroy_object)
                (reinterpret_cast<void*>(controller));
            auto weak=InterlockedDecrement(reinterpret_cast<volatile LONG*>(controller+12));
            if(weak<0) return false;
            if(weak==0) reinterpret_cast<void*(__fastcall*)(void*,uint64_t)>(base+Profile::destroy_controller)
                (reinterpret_cast<void*>(controller),1);
        }
        return true;
    }
};
using TargetSlateReferenceOps=VerifiedSlateReferenceOps<TargetViewportReferenceProfile>;
using TargetButtonReferenceOps=VerifiedSlateReferenceOps<TargetButtonReferenceProfile>;
