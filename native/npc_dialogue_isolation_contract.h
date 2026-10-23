#pragma once
#include "npc_dialogue_availability_body.h"
#include "npc_dialogue_instance_references.h"
#include "npc_dialogue_native_references.h"
namespace e33_npc_presentation {
// Read-only complete contract. Ownership, original class admission and lifecycle
// isolation remain required at the containing Curator owner boundary.
inline bool original_dialogue_isolation_contract(uint64_t base,CallIdentity actor,
        CallIdentity dialog,CallIdentity available,const std::array<CallIdentity,4>& functions){
    if(!TargetPodSchemaOps{base}.context()||!call_identity(base,available)||
       local_read<uint64_t>(available.address+32)!=dialog.address||
       !e33_mesh::named(base,local_read<uint64_t>(available.address+16),"Function","/Script/CoreUObject")||
       local_read<uint32_t>(available.address+0xb0)!=0xc420000||
       local_read<uint16_t>(available.address+0xb6)!=1||
       local_read<uint16_t>(available.address+0xb8)!=65535||
       local_read<int32_t>(available.address+0x58)!=7||
       local_read<uint64_t>(available.address+0xd8)!=base+0x13937a0)return false;
    std::array<uint64_t,15> refs{};
    if(!dialogue_local_references(base,available,refs)||
       !dialogue_instance_references(base,actor,dialog,refs)||
       !dialogue_native_references(base,functions,refs))return false;
    const auto data=local_read<uint64_t>(available.address+0x60);
    const auto count=local_read<int32_t>(available.address+0x68);
    const auto capacity=local_read<int32_t>(available.address+0x6c);
    if(data<0x10000||count!=232||capacity<count||capacity>65536)return false;
    uint8_t bytes[232]{};std::memcpy(bytes,reinterpret_cast<const void*>(data),sizeof(bytes));
    return dialogue_availability_body(bytes,sizeof(bytes),refs)&&
        call_identity(base,actor)&&call_identity(base,dialog)&&call_identity(base,available)&&
        local_read<uint64_t>(available.address+0x60)==data&&
        local_read<int32_t>(available.address+0x68)==count;
}
}
