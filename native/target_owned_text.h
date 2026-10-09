#pragma once
#include "owned_text_value.h"
#include "session_protocol.h"
#include "fixed_invocation.h"

// Candidate only; not wired to any live session. The caller must verify the
// exact executable fingerprint, own durable storage, and place every operation
// behind the native session's SEH boundary. Never use from Python/worker threads.
// Evidence: owned-text-core/lifetime/abi/vtable.json; WIDGET_LAYOUT_VALUES.md.
struct TargetOwnedTextOps {
    uint64_t base;
    bool can_release() const {
        return GetCurrentThreadId()==local_read<DWORD>(base+0x9272d30) &&
            !local_read<uint8_t>(base+0x9272cfc) && !local_read<uint8_t>(base+0x934e968);
    }
    bool can_create() const {
        return can_release() && !local_read<uint8_t>(base+0x9272cea);
    }
    bool known_text(const TargetTextValue& text) const {
        // This candidate owns only values produced by verified FromString.
        // It deliberately does not adopt arbitrary TextProperty output values.
        if(!text.data || text.flags!=2 || text.padding) return false;
        auto table=local_read<uint64_t>(text.data);
        return table==base+0x6da8c78 && local_read<int32_t>(text.data+8)>0 &&
            local_read<uint64_t>(table)==base+0x10abe30 &&
            local_read<uint64_t>(table+8)==base+0x10acdb0 &&
            local_read<uint64_t>(table+16)==base+0x10cbce0 &&
            local_read<uint64_t>(table+0x28)==base+0x10baa50;
    }
    void construct(TargetTextValue& result,const TargetStringValue& input) const {
        // Assembly: RCX=uninitialized result, RDX=read-only FString view,
        // RAX=result. The function copies every input UTF-16 unit.
        reinterpret_cast<TargetTextValue*(__fastcall*)(TargetTextValue*,const TargetStringValue*)>
            (base+0x10add50)(&result,&input);
    }
    TargetStringValue display_string(TargetTextValue& text) const {
        // This refreshes via1410c8810 then returns virtual+28's borrowed string.
        auto value=reinterpret_cast<const TargetStringValue*(__fastcall*)(TargetTextValue*)>
            (base+0x10bab10)(&text);
        return *value;
    }
    bool read_units(uint64_t address,uint16_t* output,uint32_t units) const {
        std::memcpy(output,reinterpret_cast<const void*>(address),units*sizeof(uint16_t));
        return true; // Caller SEH handles an unreadable target allocation.
    }
    void release(TargetTextValue& text) const {
        // Exact known type was checked before invoking the target release path.
        reinterpret_cast<uint64_t(__fastcall*)(void*)>(base+0x10cbce0)
            (reinterpret_cast<void*>(text.data));
    }
};
