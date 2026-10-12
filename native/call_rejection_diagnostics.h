#pragma once
#include <cstdint>
// Exact reason for the existing identity/target-state rejection202. This is
// diagnostic data, never authorization to skip cleanup or retry a dispatch.
inline uint32_t call_identity_rejection_detail(bool target_valid,bool function_valid,bool forbidden) {
    if(target_valid && function_valid && !forbidden) return 0;
    return 0x20200000u | (target_valid ? 1u : 0u) | (function_valid ? 2u : 0u) | (forbidden ? 4u : 0u);
}
