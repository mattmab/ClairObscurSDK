#pragma once
#include "binding_override_header.h"

// Exact factory-associated object observation. No engine invocation, no cache
// element or FFieldPath dereference. Actor interface +0x290 / vtable +0x10
// tail thunk 143218650 loads actor BindingOverrides +0x2f0 and jumps to
// audited lookup 142d55a30. The four private scalar reads are only
// for this exact build/class; never generalized into an arbitrary object reader.
template<class Ops>
bool empty_factory_binding_overrides(const Ops& ops,uint64_t pointer,
                                             CallIdentity& identity) {
    identity={};
    if(!ops.context() || !pointer || !ops.valid(ops.actor))return false;
    auto candidate=call_capture(ops.base,pointer);
    if(!ops.valid(candidate) || local_read<uint64_t>(pointer+32)!=ops.actor.address)return false;
    const auto cls=local_read<uint64_t>(pointer+16);
    if(!call_is_class(ops.base,cls) || !ops.named(cls,"MovieSceneBindingOverrides","/Script/MovieScene") ||
       local_read<uint32_t>(cls+0x58)!=144)return false;
    auto field=ops.field(cls,"BindingData",40,16,0x6e0de80,18014398509482497ULL);
    if(!field || (local_read<uint8_t>(field+0x70)&1))return false;
    const auto inner=local_read<uint64_t>(field+0x78);
    if(!inner || local_read<uint64_t>(inner)!=ops.base+0x6e136a0 || local_read<uint64_t>(inner+0x10)!=field ||
       local_read<uint32_t>(inner+0x30)!=1 || local_read<uint32_t>(inner+0x34)!=72 || local_read<uint32_t>(inner+0x44) ||
       !ops.script(local_read<uint64_t>(inner+0x70),"MovieSceneBindingOverrideData","/Script/MovieScene",72))return false;
    const auto observe=[&]() {
        return e33_camera_binding::FactoryOverrideState{
            local_read<e33_camera_binding::ObjectArray>(pointer+40),
            local_read<int32_t>(pointer+0x48),local_read<int32_t>(pointer+0x74),
            local_read<int32_t>(pointer+0x88),local_read<uint8_t>(pointer+0x38)};
    };
    const auto before=observe();
    if(!e33_camera_binding::factory_override_lookup_empty(before))return false;
    const auto after=observe();
    if(!e33_camera_binding::factory_override_lookup_empty(after) || before.dirty!=after.dirty ||
       !ops.valid(candidate) || !ops.valid(ops.actor) ||
       local_read<uint64_t>(ops.actor.address+752)!=pointer || local_read<uint64_t>(pointer+16)!=cls ||
       local_read<uint64_t>(pointer+32)!=ops.actor.address || local_read<uint64_t>(pointer+16)!=cls ||
       local_read<uint64_t>(ops.actor.address+752)!=pointer || !ops.context())return false;
    identity=candidate;return true;
}
