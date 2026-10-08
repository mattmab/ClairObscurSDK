#include "session_protocol.h"
#include "fixed_invocation.h"
#include "observer_core.h"
#include "console_attachment.h"

static SchedulePacket target{};
static ObserverBuffer session_events{};
static uint64_t runtime_base = 0, target_object = 0, target_function = 0;
static bool observing = false;

bool backend_shutting_down() {
    return runtime_base && local_read<uint8_t>(runtime_base + 0x9272cfc) != 0;
}
static bool lifetime_valid() {
    if (!runtime_base || backend_shutting_down() || GetCurrentThreadId() != target.target_tid) return false;
    int32_t first = local_read<int32_t>(runtime_base + 0x9361b60);
    int32_t last = local_read<int32_t>(runtime_base + 0x9361b64);
    int32_t capacity = local_read<int32_t>(runtime_base + 0x9361b68);
    return first > 0 && last == first - 1 && first <= capacity &&
        capacity <= local_read<int32_t>(runtime_base + 0x9361b84) &&
        local_read<uint8_t>(runtime_base + 0x9361b6c) == 0 &&
        target.object_index >= 0 && target.object_index < first && target.function_index >= 0 && target.function_index < first &&
        fixed_slot(runtime_base, target.object_index, target.object_serial) == target_object &&
        fixed_slot(runtime_base, target.function_index, target.function_serial) == target_function;
}
uint32_t backend_open(SessionPacket* packet) {
    // Only the fixed, already-proven getter is supported by this session version.
    target = packet->request;
    uint32_t error = invoke_fixed_guarded(&target);
    if (error) return error;
    runtime_base = reinterpret_cast<uint64_t>(GetModuleHandleW(nullptr));
    target_object = fixed_slot(runtime_base, target.object_index, target.object_serial);
    target_function = fixed_slot(runtime_base, target.function_index, target.function_serial);
    return lifetime_valid() ? 0 : 60;
}
uint32_t backend_command(SessionPacket* packet) {
    if (!lifetime_valid()) return 61;
    switch (packet->request.action) {
    case SessionConsolePoll:
        if (!attachment_valid(runtime_base)) return 132;
        packet->request.result=poll_console_command(packet->console_text)?1:0;
        packet->console_dropped=console_dropped; console_dropped=0; return 0;
    case SessionConsoleExecute:
    case SessionConsolePrint: {
        if (!attachment_valid(runtime_base)) return 132;
        size_t length=wcsnlen_s(packet->console_text,32769);
        if (length>=32769 || (packet->request.action==SessionConsoleExecute && length>4096)) return 133;
        if (packet->request.action==SessionConsolePrint) console_write(attached_console,packet->console_text);
        else {
            ConsoleString value{packet->console_text,static_cast<int32_t>(length+1),static_cast<int32_t>(length+1)};
            console_original_command(reinterpret_cast<void*>(attached_console),&value);
        }
        packet->request.result=0; return 0;
    }
    case SessionConsoleAttach: {
        if (observing) return 120;
        uint32_t error=attach_console(runtime_base,&target);
        packet->request.result=attached_console;
        return error;
    }
    case SessionConsoleDetach: return detach_console(runtime_base,false);
    case SessionConsoleStatus:
        if (attached_console && !attachment_valid(runtime_base)) return 128;
        packet->request.result=attached_console; return 0;
    case SessionEnable:
        if (observing) return 0;
        { uint32_t error = invoke_fixed_guarded(&target); if (error) return error; }
        session_events = {};
        if (!install_observer(reinterpret_cast<void* volatile*>(target_function + 0xd8),
                reinterpret_cast<ObserverEntry>(runtime_base + 0x333be80), &session_events, target_object, target.target_tid)) return 62;
        observing = true; return 0;
    case SessionDisable:
        if (!remove_observer()) return 63;
        observing = false; return 0;
    case SessionInvoke: {
        uint32_t error = invoke_fixed_guarded(&target, observing ? reinterpret_cast<uint64_t>(&observe) : 0);
        packet->request.result = target.result; return error;
    }
    case SessionDrain: drain_observer(&packet->events); return 0;
    case SessionPing: packet->request.result = observing ? 1 : 0; return 0;
    default: return 64;
    }
}
uint32_t backend_close() {
    uint32_t result = detach_console_guarded(runtime_base,backend_shutting_down());
    if (observing) {
        if (backend_shutting_down()) detach_observer_storage();
        else if (!lifetime_valid()) { detach_observer_storage(); result = 65; }
        else if (!remove_observer()) result = 66;
    }
    observing = false; runtime_base = target_object = target_function = 0;
    return result;
}
#include "session_transport.h"
