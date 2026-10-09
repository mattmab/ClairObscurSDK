#include "scheduling_protocol.h"
#include "fixed_invocation.h"
#include "target_trace_schema.h"

// Compile the real target adapter with the production identity/layout validator.
// Executable fixture coverage is separate; this is not a live validation claim.
uint32_t compile_trace_schema(uint64_t base, CallPacket& packet, e33_trace::CapturePlan& plan) {
    return prepare_target_trace_guarded(base, packet, plan);
}
