#include "session_protocol.h"
#include "fixed_invocation.h"
#include "observer_core.h"
#include "console_attachment.h"
#ifdef E33_POD_SESSION
#include "target_pod_schema.h"
static bool validate_target_pod(uint64_t base,uint64_t property,PodValueKind kind,const CallIdentity& id) {
    TargetPodSchemaOps ops{base};
    return validate_pod_parameter(ops,property,kind,id);
}
static const CallPodValidation pod_validation{validate_target_pod};
static const CallPodValidation* session_pod_validation=&pod_validation;
#elif defined(E33_REFLECTED_SESSION)
#include "reflected_invocation.h"
static const CallPodValidation* session_pod_validation=nullptr;
#endif
#ifdef E33_ASSIGNMENT_SESSION
#include "target_object_assignment.h"
#endif
#ifdef E33_ENUM_SESSION
#include "enum_schema.h"
static bool validate_target_enum(uint64_t base,uint64_t property,const CallIdentity& id,const uint8_t* value) {
    TargetPodSchemaOps ops{base};
    return value ? validate_byte_enum_value(ops,property,id,*value) : validate_byte_enum_parameter(ops,property,id);
}
#endif
#ifdef E33_REFLECTED_SESSION
#include "reflected_invocation.h"
#endif
#ifdef E33_LEASE_SESSION
#include "target_strong_reference.h"
#include "strong_lease_pool.h"
#ifdef E33_STABLE_SESSION
#include "stable_identity.h"
#endif
static StrongLeasePool<> session_leases;
static uint64_t lease_session=0;
#endif

static SchedulePacket target{};
static ObserverBuffer session_events{};
static uint64_t runtime_base = 0, target_object = 0, target_function = 0;
static bool observing = false;
static unsigned console_toggle_key=0;
#ifdef E33_TEXT_SESSION
#include "target_text_call.h"
// Never borrow the shared mapping for ownership or cleanup. These records live
// in the pinned module even after a controller exits or an engine call faults.
static TextCallPacket session_text_packet;
static TargetTextCall session_text;
static TextFrameResult guarded_text_cleanup() {
    __try {
        TargetOwnedTextOps ops{session_text.base};
        return session_text.frame.cleanup(ops);
    } __except(EXCEPTION_EXECUTE_HANDLER) { return TextFrameResult::Quarantined; }
}
static uint32_t guarded_text_invoke(const CallRetention* retention) {
    __try {
        const auto handling=session_text.handling();
        return reflected_call(session_text.base,session_text_packet.retained.call,
                              retention,session_pod_validation,&handling);
    } __except(EXCEPTION_EXECUTE_HANDLER) { return 708; }
}
#endif
#ifdef E33_RETAINED_SESSION
static uint32_t retain_preflight(void*,const CallPacket& call) {
    return static_cast<uint32_t>(session_leases.preflight(lease_session,retained_call_slots(call)));
}
static uint32_t retain_output(void* context,uint32_t offset,CallIdentity& identity) {
    auto& retained=*static_cast<RetainedCallPacket*>(context);
    if(retained.count>=kCallObjects) return 401;
    TargetStrongReferenceOps ops{runtime_base,identity};
    uint64_t token=0;
    auto result=session_leases.acquire(ops,lease_session,identity.address,token);
    if(result!=StrongLeaseResult::Ok) return static_cast<uint32_t>(result);
    retained.leases[retained.count++]={offset,token};
#ifdef E33_STABLE_SESSION
    // The pool already owns this object before any serial-allocation side effect.
    if(!stabilize_retained_identity(ops,identity)) return 413;
#endif
    return 0;
}
#endif

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
#ifdef E33_TEXT_SESSION
    // Failed ownership from a previous session is never adopted by a new owner.
    if(!session_text.frame.available()) return 230;
#endif
    // Opening first verifies the fixed, already-proven getter and target thread.
    target = packet->request;
    uint32_t error = invoke_fixed_guarded(&target);
    if (error) return error;
    runtime_base = reinterpret_cast<uint64_t>(GetModuleHandleW(nullptr));
    target_object = fixed_slot(runtime_base, target.object_index, target.object_serial);
    target_function = fixed_slot(runtime_base, target.function_index, target.function_serial);
    if(!lifetime_valid()) return 60;
#ifdef E33_LEASE_SESSION
    auto lease_error=session_leases.begin(packet->request.nonce);
    if(lease_error!=StrongLeaseResult::Ok) return static_cast<uint32_t>(lease_error);
    lease_session=packet->request.nonce;
#endif
    return 0;
}
uint32_t backend_command(SessionPacket* packet) {
    if (!lifetime_valid()) return 61;
    switch (packet->request.action) {
#ifdef E33_TEXT_SESSION
    case SessionTextInvoke: {
        if(!session_text.frame.available()) { packet->text.retained.call.error=230; return 0; }
        session_text_packet=packet->text;
        session_text.base=runtime_base;
        session_text.packet=&session_text_packet;
        CallRetention retention{&session_text_packet.retained,retain_preflight,retain_output};
        auto error=guarded_text_invoke(&retention);
        // Includes normal pre/post-dispatch rejection and guarded SEH failure.
        // Unknown dispatch ownership is quarantined, never destructed or retried.
        const auto cleaned=guarded_text_cleanup();
        if(!error) error=TargetTextCall::error(cleaned);
        session_text_packet.retained.call.error=error;
        packet->text=session_text_packet;
        // Reset only after all owners were released. A deferred or uncertain
        // frame rejects subsequent text calls and remains available for close.
        session_text.frame.reset();
        return 0;
    }
#endif
#ifdef E33_ASSIGNMENT_SESSION
    case SessionObjectAssign: {
        auto& wire=packet->assignment;
        auto& assignment=wire.assignment;
        if(wire.version!=1 || wire.error || !valid_object_assignment(assignment)) {
            wire.error=6; return 0;
        }
        if(!session_leases.owns_object(lease_session,wire.target_token,assignment.target.address) ||
           (assignment.expected.address ? !session_leases.owns_object(lease_session,wire.expected_token,assignment.expected.address) : wire.expected_token!=0) ||
           (assignment.value.address ? !session_leases.owns_object(lease_session,wire.value_token,assignment.value.address) : wire.value_token!=0)) {
            wire.error=7; return 0;
        }
        TargetObjectAssignmentOps ops{runtime_base};
        wire.error=static_cast<uint32_t>(assign_object_property(ops,assignment));
        return 0;
    }
#endif
#ifdef E33_RETAINED_SESSION
    case SessionRetainedInvoke: {
        auto& retained=packet->retained;
        if(!retained_call_empty(retained)) { retained.call.error=412; return 0; }
        CallRetention retention{&retained,retain_preflight,retain_output};
#ifdef E33_ENUM_SESSION
        if(retained.call.version==kEnumCallVersion) {
            CallEnumValidation enums{&retained,validate_target_enum};
            retained.call.error=reflected_call(runtime_base,retained.call,&retention,session_pod_validation,nullptr,&enums);
            return 0;
        }
#endif
        retained.call.error=reflected_call(runtime_base,retained.call,&retention,session_pod_validation);
        return 0;
    }
#endif
#ifdef E33_LEASE_SESSION
    case SessionLeaseAcquire:
    case SessionLeaseRelease:
    case SessionLeaseStatus: {
        auto& lease=packet->lease;
        bool empty=lease.object.index==-1 && !lease.object.serial && !lease.object.address;
        if(lease.version!=kLeaseVersion || lease.error || lease.outcome || lease.active ||
           (packet->request.action==SessionLeaseAcquire &&
               (lease.token || lease.object.index<0 || !lease.object.address)) ||
           (packet->request.action!=SessionLeaseAcquire && !empty) ||
           (packet->request.action==SessionLeaseStatus && lease.token)) {
            lease.error=411; lease.outcome=LeaseNotDispatched; return 0;
        }
        TargetStrongReferenceOps ops{runtime_base,lease.object};
        lease.outcome=LeaseUnknown;
        StrongLeaseResult result=StrongLeaseResult::Ok;
        if(packet->request.action==SessionLeaseAcquire)
            result=session_leases.acquire(ops,lease_session,lease.object.address,lease.token);
        else if(packet->request.action==SessionLeaseRelease)
            result=session_leases.release(ops,lease_session,lease.token);
        lease.error=static_cast<uint32_t>(result);
        lease.active=session_leases.active();
        lease.outcome=LeaseCompleted;
        return 0;
    }
#endif
#ifdef E33_REFLECTED_SESSION
    case SessionReflectedInvoke:
        packet->call.error=reflected_call(runtime_base,packet->call,nullptr,session_pod_validation);
        return 0; // A rejected plan is a normal response, not a transport failure.
#endif
    case SessionConsoleKey: {
        if (!attachment_valid(runtime_base)) return 132;
        wchar_t* end=nullptr;
        unsigned long key=wcstoul(packet->console_text,&end,10);
        if (!end || end==packet->console_text || *end || (key && (key<VK_F1 || key>VK_F12))) return 135;
        if (!exact_name(runtime_base,runtime_base+0x94dfb50,"Typing") ||
            !exact_name(runtime_base,runtime_base+0x94dfb58,"Open")) return 136;
        console_toggle_key=static_cast<unsigned>(key); packet->request.result=key; return 0;
    }
    case SessionConsoleNames:
        if (!attachment_valid(runtime_base)) return 132;
        if (!set_console_names(packet->console_text)) return 134;
        packet->request.result=0; return 0;
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
    case SessionConsoleDetach: console_toggle_key=0; return detach_console(runtime_base,false);
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
#ifdef E33_LEASE_SESSION
static StrongLeaseResult guarded_lease_close() {
    __try {
        TargetStrongReferenceOps ops{runtime_base,{-1,0,0}};
        return session_leases.close(ops,lease_session);
    } __except(EXCEPTION_EXECUTE_HANDLER) { return StrongLeaseResult::Quarantined; }
}
#endif
uint32_t backend_close() {
    uint32_t lease_cleanup_error=0;
#ifdef E33_TEXT_SESSION
    const auto text_cleanup=guarded_text_cleanup();
    if(text_cleanup==TextFrameResult::CleanupDeferred && !backend_shutting_down())
        return kSessionCloseDeferred;
    if(text_cleanup==TextFrameResult::Ok) session_text.frame.reset();
    else if(!backend_shutting_down()) lease_cleanup_error=TargetTextCall::error(text_cleanup);
    // On terminal teardown or uncertain ownership, the pinned module retains
    // the bounded frame. It is not unloaded, reset, or reused by a new session.
#endif
#ifdef E33_LEASE_SESSION
    if(lease_session) {
        auto result=guarded_lease_close();
        // A normal GC interval may defer release. Keep the GT cleanup hook and
        // owner tracking until a subsequent message can finish the close.
        if(result==StrongLeaseResult::Deferred && !backend_shutting_down())
            return kSessionCloseDeferred;
        if(result==StrongLeaseResult::Ok) lease_session=0;
        else if(!backend_shutting_down() && !lease_cleanup_error) lease_cleanup_error=static_cast<uint32_t>(result);
        // During terminal engine teardown, engine-owned vtables remain valid;
        // quarantined storage is bounded and never reused by another session.
    }
#endif
    console_toggle_key=0;
    uint32_t result = detach_console_guarded(runtime_base,backend_shutting_down());
    if(!result) result=lease_cleanup_error;
    if (observing) {
        if (backend_shutting_down()) detach_observer_storage();
        else if (!lifetime_valid()) { detach_observer_storage(); result = 65; }
        else if (!remove_observer()) result = 66;
    }
    observing = false; runtime_base = target_object = target_function = 0;
    return result;
}
void backend_message(MSG* message) {
    if (!console_toggle_key || message->wParam!=console_toggle_key ||
        (message->message!=WM_KEYDOWN && message->message!=WM_SYSKEYDOWN &&
         message->message!=WM_KEYUP && message->message!=WM_SYSKEYUP)) return;
    if ((GetKeyState(VK_CONTROL)&0x8000) || (GetKeyState(VK_MENU)&0x8000) || (GetKeyState(VK_SHIFT)&0x8000)) return;
    if (!lifetime_valid() || !attachment_valid(runtime_base)) { console_toggle_key=0; return; }
    bool pressed=message->message==WM_KEYDOWN || message->message==WM_SYSKEYDOWN;
    bool repeat=(message->lParam & (LPARAM(1)<<30))!=0;
    message->message=WM_NULL;
    if (!pressed || repeat) return;
    uint64_t current=local_read<uint64_t>(attached_console+0xd8);
    uint64_t open=local_read<uint64_t>(runtime_base+0x94dfb58);
    uint64_t typing=local_read<uint64_t>(runtime_base+0x94dfb50);
    uint64_t transition=local_read<uint64_t>(local_read<uint64_t>(attached_console)+0x3c8);
    if ((current && current!=open && current!=typing) || transition!=runtime_base+0x3dcff60) { console_toggle_key=0; return; }
    using Transition=void(__fastcall*)(void*,uint64_t);
    reinterpret_cast<Transition>(transition)(reinterpret_cast<void*>(attached_console),current?0:open);
}
#include "session_transport.h"
