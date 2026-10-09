#include "scheduling_protocol.h"
#include "fixed_invocation.h"
#include "target_trace_schema.h"
#include "target_trace_collector.h"
#include "target_trace_registry.h"

static e33_trace::Registry<TargetTraceOps> compile_registry;
void compile_registry_command(e33_trace::Packet& packet) { compile_registry.command(packet); }
uint32_t compile_registry_close(bool terminal) { return compile_registry.close(terminal); }

// Compile the real target adapter with the production identity/layout validator.
// Executable fixture coverage is separate; this is not a live validation claim.
uint32_t compile_trace_schema(uint64_t base, CallPacket& packet, e33_trace::CapturePlan& plan) {
    return prepare_target_trace_guarded(base, packet, plan);
}

bool compile_trace_collect(TargetTraceContext& context, void* object, void* frame, void* result,
                          e33_trace::Identity& identity, e33_trace::Copy& copied) {
    return target_trace_collect(&context, object, frame, result, identity, copied);
}
