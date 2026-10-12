#pragma once
#include "bound_object_frame.h"

namespace e33_camera_binding {
struct FactoryOverrideState {
    ObjectArray bindings;
    int32_t sparse_count,free_count,hash_size;
    uint8_t dirty;
};
// Exact constructor-empty semantics audited in 142d40660 / 142d55a30.
// No assumption about allocator pointers, slack bytes or bucket contents.
inline bool factory_override_lookup_empty(const FactoryOverrideState& state) {
    return !state.bindings.data && !state.bindings.count && !state.bindings.capacity &&
        !state.sparse_count && !state.free_count && !state.hash_size && state.dirty<=1;
}
// Header validation only. Empty BindingData is NOT yet proof that the private
// lookup cache has no effective overrides. This helper is not an admission gate.
inline bool empty_override_array(const ObjectArray& value) {
    return value.count==0 && value.capacity>=0 && value.capacity<=64 &&
        (value.capacity ? value.data && !(value.data&7) : !value.data) &&
        value.data<=UINT64_MAX-uint64_t(value.capacity)*72;
}
}

