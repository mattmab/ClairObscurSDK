#pragma once
#include "invocation_protocol.h"
constexpr uint32_t SessionSequenceOwner=115;
#pragma pack(push,1)
struct SequenceOwnerPacket {
    uint32_t version,operation;
    uint64_t owner,reserved;
    uint32_t error,state;
    CallPacket stop,destroy;
};
#pragma pack(pop)
static_assert(sizeof(SequenceOwnerPacket)==49328);
