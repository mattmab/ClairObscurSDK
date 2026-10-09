#pragma once
#include "pod_schema.h"

// Target-derived, read-only gate for scalar byte-backed EnumProperty. Caller
// supplies fault containment and a current game-thread context. Membership is
// not semantic permission: enum sentinels/flags require a caller policy too.
template<class Ops>
bool validate_byte_enum_parameter(Ops& ops,uint64_t property,const CallIdentity& identity) {
    if(!property || !ops.context() || !ops.identity(identity) ||
       ops.template read<uint64_t>(property)!=ops.base+0x6deeee8 ||
       !ops.name(ops.template read<uint64_t>(property+8),"EnumProperty") ||
       ops.template read<uint32_t>(property+0x30)!=1 ||
       ops.template read<uint32_t>(property+0x34)!=1 ||
       ops.template read<uint64_t>(property+0x78)!=identity.address) return false;
    const auto child=ops.template read<uint64_t>(property+0x70);
    if(!child || child==property ||
       ops.template read<uint64_t>(child+0x10)!=property ||
       !ops.name(ops.template read<uint64_t>(child+8),"ByteProperty") ||
       ops.template read<uint32_t>(child+0x30)!=1 ||
       ops.template read<uint32_t>(child+0x34)!=1 ||
       ops.template read<uint32_t>(child+0x44)!=0 ||
       ops.template read<uint64_t>(child+0x70)) return false;
    const auto object=identity.address;
    if(!pod_registered(ops,object) || ops.template read<uint64_t>(object)!=ops.base+0x6dee0b0)
        return false;
    const auto cls=ops.template read<uint64_t>(object+0x10);
    if(!pod_registered(ops,cls) || !ops.name(cls+0x18,"Enum") ||
       !pod_package(ops,ops.template read<uint64_t>(cls+0x20),"/Script/CoreUObject")) return false;
    const auto count=ops.template read<int32_t>(object+0x48);
    const auto capacity=ops.template read<int32_t>(object+0x4c);
    const auto data=ops.template read<uint64_t>(object+0x40);
    return count>0 && count<=capacity && capacity<=65536 && data &&
        ops.identity(identity) && ops.context();
}

template<class Ops>
bool validate_byte_enum_value(Ops& ops,uint64_t property,const CallIdentity& identity,uint8_t value) {
    if(!validate_byte_enum_parameter(ops,property,identity)) return false;
    const auto object=identity.address;
    const auto data=ops.template read<uint64_t>(object+0x40);
    const auto count=ops.template read<int32_t>(object+0x48);
    const auto capacity=ops.template read<int32_t>(object+0x4c);
    if(!data || count<=0 || count>capacity || capacity>65536) return false;
    bool found=false;
    for(int32_t i=0;i<count;++i)
        found |= ops.template read<int64_t>(data+uint64_t(i)*16+8)==value;
    return found && ops.template read<uint64_t>(object+0x40)==data &&
        ops.template read<int32_t>(object+0x48)==count &&
        ops.template read<int32_t>(object+0x4c)==capacity &&
        validate_byte_enum_parameter(ops,property,identity);
}
