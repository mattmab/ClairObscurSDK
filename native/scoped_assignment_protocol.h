#pragma once
#include "assignment_protocol.h"
constexpr uint32_t SessionScopedAssignment=116;
#pragma pack(push,1)
struct ScopedAssignmentPacket {
    uint32_t version,operation;
    uint64_t owner,reserved;
    uint32_t error,state;
    AssignmentPacket assignment;
};
#pragma pack(pop)
static_assert(sizeof(ScopedAssignmentPacket)==264);
