#pragma once
#include <cstdint>
#include <cstring>
#include "owned_action_clone.h"

namespace e33_action_clone {
inline constexpr uint64_t array_property_table=0x6e0de80;
inline constexpr uint64_t array_copy_entry=0x133a6f0;
inline constexpr uint8_t array_copy_prefix[]={0x48,0x89,0x5c,0x24,0x10,0x48,0x89,0x6c,0x24,0x18,
    0x48,0x89,0x74,0x24,0x20,0x48,0x89,0x4c,0x24,0x08,0x57,0x41,0x54,0x41,0x55,0x41,0x56,
    0x41,0x57,0x48,0x83,0xec,0x50};
// Internal native capability, never a wire-supplied property/address profile.
// The target adapter establishes ownership + exact Sequential/Wrapper schema
// and returns only the two value-storage addresses for that one property.
struct RootArrayCopy {
    uint64_t property=0,source_value=0,destination_value=0;
};
template<class Ops> bool array_copy_engine_ready(Ops& ops) {
    return ops.context() && ops.template read<uint64_t>(ops.base+array_property_table+0xf0)==ops.base+array_copy_entry &&
        ops.bytes(ops.base+array_copy_entry,array_copy_prefix,sizeof(array_copy_prefix));
}
template<class Ops> Result copy_owned_simon_wrappers(Ops& ops) {
    RootArrayCopy copy{};
    // Admission MUST prove current exact original Simon root, newly constructed
    // owned same-class destination, complete ten-element source, independent
    // initialized empty destination, exact full ArrayProperty/inner Wrapper
    // metadata and all retained source identities. No client can select a field.
    if(!ops.admit_exact_simon_root_array(copy) || !copy.property || !copy.source_value ||
       !copy.destination_value || copy.source_value==copy.destination_value ||
       !array_copy_engine_ready(ops) ||
       ops.template read<uint64_t>(copy.property)!=ops.base+array_property_table) return Result::not_dispatched;
    ops.publish_array_copy_unknown(copy); // Durable before allocator/inner-copy.
    ops.copy_array(copy); // Target uses fixed ABI below, never a selected thunk.
    if(!ops.verify_independent_simon_array_and_unchanged_source(copy)) return Result::unknown;
    return Result::returned;
}
// Shipping CopyScriptStruct at RVA0x127a110 calls this FProperty virtual slot
// with exactly (property,destinationValue,sourceValue,ArrayDim). Disassembly of
// FArrayProperty RVA0x133a6f0 confirms engine allocator and inner-field copy.
inline void dispatch_simon_array_copy(uint64_t base,const RootArrayCopy& copy) {
    using Copy=void(*)(void*,void*,const void*,int);
    reinterpret_cast<Copy>(base+array_copy_entry)(reinterpret_cast<void*>(copy.property),
        reinterpret_cast<void*>(copy.destination_value),reinterpret_cast<const void*>(copy.source_value),1);
}
}
