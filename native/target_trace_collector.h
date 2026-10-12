#pragma once
#include "target_trace_schema.h"
#include "trace_events.h"
#include "blueprint_trace_frame.h"

struct TargetTraceContext {
    uint64_t base{};
    CallIdentity function{}, owner{}, filter{};
    uint32_t thread{}, pid{};
    bool filtered{};
    e33_trace::CapturePlan plan{};
};

inline bool target_trace_read(uint64_t address, void* output, uint32_t size) {
    if (!address || !size || size > e33_trace::max_bytes || address > UINT64_MAX - (size - 1)) return false;
    __try { std::memcpy(output, reinterpret_cast<const void*>(address), size); return true; }
    __except(EXCEPTION_EXECUTE_HANDLER) { return false; }
}

#ifdef E33_BLUEPRINT_DIRECT_SESSION
#include "blueprint_direct_trace.h"
#endif

inline bool target_trace_gate(const TargetTraceContext& context) {
    const auto base = context.base;
    return base && context.pid == GetCurrentProcessId() && context.thread == GetCurrentThreadId() &&
        local_read<DWORD>(base + 0x9272d30) == context.thread &&
        !local_read<uint8_t>(base + 0x9272cfc) && !local_read<uint8_t>(base + 0x934e968) &&
        !local_read<uint8_t>(base + 0x9272cea) &&
        call_identity(base, context.function) && call_identity(base, context.owner) &&
        !(local_read<uint32_t>(context.function.address + 8) & 0x40000000) &&
        !(local_read<uint32_t>(context.owner.address + 8) & 0x40000000) &&
        local_read<uint64_t>(context.function.address + 0x20) == context.owner.address;
}

inline uint32_t prepare_target_trace_context(uint64_t base, CallPacket& schema,
                                            const CallIdentity* filter, TargetTraceContext& output) {
    output = {};
    __try {
        TargetTraceContext candidate{};
        if (auto error = prepare_target_trace_guarded(base, schema, candidate.plan)) return error;
        candidate.base = base; candidate.function = schema.function;
        candidate.owner = call_capture(base, local_read<uint64_t>(schema.function.address + 0x20));
        candidate.thread = GetCurrentThreadId(); candidate.pid = GetCurrentProcessId();
        if (!target_trace_gate(candidate)) return 926;
        if (filter) {
            const auto object = call_identity(base, *filter);
            if (!object || (local_read<uint32_t>(object + 8) & 0x40000000) ||
                !call_derives(base, local_read<uint64_t>(object + 0x10), candidate.owner.address)) return 927;
            candidate.filtered = true; candidate.filter = *filter;
        }
        output = candidate; return 0;
    } __except(EXCEPTION_EXECUTE_HANDLER) { output = {}; return 924; }
}

inline bool target_trace_collect_body(const TargetTraceContext& context, void* object,
                                      void* frame, void* result, e33_trace::Identity& identity,
                                      e33_trace::Copy& copied) {
    if (!target_trace_gate(context) || !object) return false;
    const auto address = reinterpret_cast<uint64_t>(object);
    const auto observed = call_capture(context.base, address);
    if (!observed.address || observed.serial < 0 || !call_identity(context.base, observed) ||
        (local_read<uint32_t>(address + 8) & 0x40000000) ||
        !call_derives(context.base, local_read<uint64_t>(address + 0x10), context.owner.address)) return false;
    if (context.filtered && (observed.index != context.filter.index ||
        observed.serial != context.filter.serial || observed.address != context.filter.address)) return false;
    e33_trace::FrameStorage storage{};
    if (context.plan.blueprint) {
        const auto script = local_read<uint64_t>(context.function.address + 0x60);
        if (e33_trace::resolve_blueprint_entry(target_trace_read, reinterpret_cast<uint64_t>(frame),
            context.function.address, address, script, storage
#ifdef E33_BLUEPRINT_DIRECT_SESSION
            ,blueprint_direct_frame
#endif
            ) != e33_trace::FrameError::none) return false;
        e33_trace::Copy candidate{};
        for (uint32_t i = 0; i < context.plan.count; ++i) {
            const auto& field = context.plan.fields[i];
            if (field.source != e33_trace::StorageKind::locals || field.size != 8 ||
                uint64_t(field.source_offset) + 8 > field.source_extent ||
                storage.locals > UINT64_MAX - field.source_offset - 7) return false;
            const auto& constraint = context.plan.constraints[i];
            if (constraint.address) {
                uint64_t pointer{};
                if (!target_trace_read(storage.locals + field.source_offset, &pointer, 8) ||
                    uint64_t(field.destination_offset) + sizeof(CallIdentity) > context.plan.extent) return false;
                const auto value = call_capture(context.base, pointer);
                if (pointer && (!value.address || value.serial < 0 || !call_identity(context.base, value) ||
                    !call_identity(context.base, constraint) || (local_read<uint32_t>(pointer + 8) & 0x40000000) ||
                    !call_derives(context.base, local_read<uint64_t>(pointer + 0x10), constraint.address))) return false;
                std::memcpy(candidate.bytes + field.destination_offset, &value, sizeof(value));
            } else {
                if (uint64_t(field.destination_offset) + 8 > context.plan.extent ||
                    !target_trace_read(storage.locals + field.source_offset, candidate.bytes + field.destination_offset, 8)) return false;
            }
        }
        candidate.size = context.plan.extent; copied = candidate;
        identity = {context.pid, observed.index, observed.serial};
        return true;
    }
    if (e33_trace::resolve_frame(target_trace_read, reinterpret_cast<uint64_t>(frame),
        context.function.address, reinterpret_cast<uint64_t>(result), storage) != e33_trace::FrameError::none)
        return false;
    if (e33_trace::capture_fields(target_trace_read, storage, context.plan.fields,
        context.plan.count, context.plan.extent, copied) != e33_trace::CaptureError::none) return false;
    identity = {context.pid, observed.index, observed.serial};
    return true;
}

// Exact Registration::Collector signature. No engine functions are invoked and
// only copied scalar data/registry identity leave the callback. The context and
// reflection plan remain owned by the registration until callback detachment.
inline bool target_trace_collect(void* context, void* object, void* frame, void* result,
                                 e33_trace::Identity& identity, e33_trace::Copy& copied) {
    identity = {}; copied = {};
    __try {
        if (context && target_trace_collect_body(*static_cast<TargetTraceContext*>(context),
                                                 object, frame, result, identity, copied)) return true;
    } __except(EXCEPTION_EXECUTE_HANDLER) {}
    identity = {}; copied = {}; return false;
}
