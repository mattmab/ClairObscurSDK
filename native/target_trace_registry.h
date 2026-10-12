#pragma once
#include "target_trace_collector.h"
#include "trace_registry.h"

struct TargetTraceOps {
    using Context = TargetTraceContext;
    static uint32_t prepare(uint64_t base, CallPacket& schema, const CallIdentity* filter, Context& context) {
        auto error=prepare_target_trace_context(base, schema, filter, context);
#ifdef E33_BLUEPRINT_DIRECT_SESSION
        if (!error && context.plan.blueprint && !BlueprintDirectTrace::install(base,context.function.address)) return 940;
#endif
        return error;
    }
#ifdef E33_BLUEPRINT_DIRECT_SESSION
    static void close_blueprint() { BlueprintDirectTrace::close(); }
    static bool is_blueprint(const Context& context) { return context.plan.blueprint; }
#endif
    static e33_trace::Storage storage(const Context& context) {
        __try {
            if (context.thread != GetCurrentThreadId()) return e33_trace::Storage::deferred;
            if (local_read<uint8_t>(context.base + 0x9272cfc)) return e33_trace::Storage::lost;
            if (local_read<uint8_t>(context.base + 0x934e968) || local_read<uint8_t>(context.base + 0x9272cea))
                return e33_trace::Storage::deferred;
            if (!call_identity(context.base, context.function) ||
                (local_read<uint32_t>(context.function.address + 8) & 0x40000000)) return e33_trace::Storage::lost;
            return e33_trace::Storage::ready;
        } __except(EXCEPTION_EXECUTE_HANDLER) { return e33_trace::Storage::lost; }
    }
    static void* volatile* entry(const Context& context) {
        return reinterpret_cast<void* volatile*>(context.function.address + 0xd8);
    }
    static e33_trace::Entry expected(uint64_t base, const CallPacket& schema) {
        return reinterpret_cast<e33_trace::Entry>(base + schema.entry_rva);
    }
    static bool collect(void* context, void* object, void* frame, void* result,
                        e33_trace::Identity& identity, e33_trace::Copy& copied) {
        return target_trace_collect(context, object, frame, result, identity, copied);
    }
};
