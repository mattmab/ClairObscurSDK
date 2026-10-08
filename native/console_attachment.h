#pragma once
#include "console_construction.h"

static uint64_t attached_console = 0, attached_viewport = 0;
static int32_t console_index = -1, viewport_index = -1;
static int32_t console_serial = 0, viewport_serial = 0;
inline int32_t current_serial(uint64_t base, int32_t index) {
    if (index<0 || index>=local_read<int32_t>(base+0x9361b84) ||
        (index>>16)>=local_read<int32_t>(base+0x9361b8c)) return INT32_MIN;
    uint64_t chunks=local_read<uint64_t>(base+0x9361b70);
    return local_read<int32_t>(local_read<uint64_t>(chunks+uint64_t(index>>16)*8)+uint64_t(index&65535)*24+0x10);
}
inline bool attachment_valid(uint64_t base) {
    if (!attached_console || !attached_viewport) return false;
    // A serial can be assigned lazily. A nonzero captured serial must never change.
    int32_t cs=current_serial(base,console_index), vs=current_serial(base,viewport_index);
    if (cs==INT32_MIN || vs==INT32_MIN) return false;
    return (!console_serial || cs==console_serial) && (!viewport_serial || vs==viewport_serial) &&
        fixed_slot(base,console_index,cs)==attached_console && fixed_slot(base,viewport_index,vs)==attached_viewport &&
        local_read<uint64_t>(attached_viewport+0x40)==attached_console &&
        local_read<uint64_t>(attached_console+0x20)==attached_viewport &&
        local_read<uint64_t>(attached_console)==base+0x7818778;
}
inline uint32_t attach_console(uint64_t base, SchedulePacket* packet) {
    if (attached_console) return attachment_valid(base) ? 0 : 121;
    uint32_t error=construct_console_guarded(packet);
    if (error) return error;
    uint64_t console=packet->result, viewport=local_read<uint64_t>(console+0x20);
    if (local_read<uint64_t>(viewport+0x40)!=0 || local_read<uint8_t>(base+0x934e968)) return 122;
    console_index=local_read<int32_t>(console+12); viewport_index=local_read<int32_t>(viewport+12);
    console_serial=current_serial(base,console_index); viewport_serial=current_serial(base,viewport_index);
    // On the verified GameThread with no incremental-reachability phase active.
    // This reflected UObject reference retains the console while attached.
    if (InterlockedCompareExchangePointer(reinterpret_cast<void* volatile*>(viewport+0x40),
            reinterpret_cast<void*>(console),nullptr)!=nullptr) return 123;
    attached_console=console; attached_viewport=viewport;
    return attachment_valid(base) ? 0 : 124;
}
inline uint32_t detach_console(uint64_t base, bool shutting_down) {
    if (!attached_console) return 0;
    uint32_t error=0;
    if (!shutting_down) {
        if (!attachment_valid(base)) error=125;
        else {
            uint64_t transition=local_read<uint64_t>(local_read<uint64_t>(attached_console)+0x3c8);
            if (transition!=base+0x3dcff60) return 126;
            using Transition=void(__fastcall*)(void*,uint64_t);
            reinterpret_cast<Transition>(transition)(reinterpret_cast<void*>(attached_console),0);
            if (InterlockedCompareExchangePointer(reinterpret_cast<void* volatile*>(attached_viewport+0x40),nullptr,
                    reinterpret_cast<void*>(attached_console))!=reinterpret_cast<void*>(attached_console)) error=127;
        }
    }
    // During exit purge never dereference cached engine objects.
    attached_console=attached_viewport=0; console_index=viewport_index=-1;
    console_serial=viewport_serial=0;
    return error;
}
inline uint32_t detach_console_guarded(uint64_t base, bool shutting_down) {
    __try { return detach_console(base,shutting_down); }
    __except(EXCEPTION_EXECUTE_HANDLER) { return 129; }
}
