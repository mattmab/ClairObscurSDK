#pragma once
#include "reflected_invocation.h"
#include "trace_plan.h"

// Called only on the game thread before installing an observer. The schema's
// target is an exemplar for owner/dispatcher validation, not implicitly a trace
// target filter. The registration layer must separately retain that choice.
inline uint32_t prepare_target_trace(uint64_t base, CallPacket& schema,
                                    e33_trace::CapturePlan& output) {
    output = {};
    // Reject unsupported codecs and non-observation packet data before touching
    // engine state. No arguments are executed or native values constructed.
    if (validate_call_packet(schema) || schema.object_count) return 920;
    for (auto byte : schema.data) if (byte) return 920;
    for (uint32_t i = 0; i < schema.field_count; ++i)
        if (schema.fields[i].kind > CallDouble) return 921;
    if (local_read<uint8_t>(base + 0x9272cea)) return 925;
    if (auto error = reflected_call(base, schema, nullptr, nullptr, nullptr, nullptr, true))
        return error;
    uint64_t properties[kCallFields]{};
    auto property = local_read<uint64_t>(schema.function.address + 0x50);
    uint32_t count = 0, walked = 0;
    for (; property; property = local_read<uint64_t>(property + 0x18)) {
        if (++walked > 4096) return 922;
        if (!(local_read<uint64_t>(property + 0x38) & 0x80)) continue;
        if (count == kCallFields) return 922;
        properties[count++] = property;
    }
    return e33_trace::make_capture_plan(schema, properties, count, output) ? 0 : 923;
}

inline uint32_t prepare_target_trace_guarded(uint64_t base, CallPacket& schema,
                                            e33_trace::CapturePlan& output) {
    __try { return prepare_target_trace(base, schema, output); }
    __except(EXCEPTION_EXECUTE_HANDLER) { output = {}; return 924; }
}
