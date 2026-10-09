#pragma once
#include "invocation_protocol.h"

constexpr uint32_t kLeaseVersion=1;
enum : uint32_t { LeaseNotDispatched=0, LeaseCompleted=1, LeaseUnknown=2 };
#pragma pack(push,1)
struct LeasePacket {
    uint32_t version=kLeaseVersion, error=0, outcome=LeaseNotDispatched, active=0;
    CallIdentity object{-1,0,0};
    uint64_t token=0;
};
#pragma pack(pop)
static_assert(sizeof(LeasePacket)==40);
