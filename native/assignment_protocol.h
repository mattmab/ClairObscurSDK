#pragma once
#include "object_assignment.h"
#pragma pack(push, 1)
struct AssignmentPacket {
    uint32_t version=1, error=0;
    uint64_t target_token=0, expected_token=0, value_token=0;
    ObjectAssignment assignment;
};
#pragma pack(pop)
static_assert(sizeof(AssignmentPacket)==232);
