#pragma once
#include "invocation_protocol.h"

// Separate v8 envelope: the established CallPacket stays byte-for-byte stable.
#pragma pack(push,1)
struct CallLease { uint32_t offset=0; uint64_t token=0; };
struct RetainedCallPacket {
    CallPacket call{};
    uint32_t version=1, count=0;
    CallLease leases[kCallObjects]{};
};
#pragma pack(pop)
static_assert(sizeof(RetainedCallPacket)==26192);

inline bool call_output_object(const CallField& field) {
    return (field.kind==CallObject || field.kind==CallClass) && (field.flags&0x500);
}
inline uint32_t retained_call_slots(const CallPacket& call) {
    uint32_t count=0;
    for(uint32_t i=0;i<call.field_count;++i)
        if(call_output_object(call.fields[i])) count+=call.fields[i].dimension;
    return count;
}
inline bool retained_call_empty(const RetainedCallPacket& packet) {
    if(packet.version!=1 || packet.count) return false;
    for(const auto& lease:packet.leases) if(lease.offset || lease.token) return false;
    return true;
}
