#pragma once
#include <cstdint>
constexpr uint32_t SessionLeasePolicy=120;
#pragma pack(push,1)
struct LeaseOwnerStats { uint64_t owner;uint32_t active,peak; };
struct LeasePolicyPacket {
    uint32_t version,operation,limit,quota,reserve,error,active,peak,capacity,count;
    uint64_t storage_bytes;
    LeaseOwnerStats owners[64];
};
#pragma pack(pop)
static_assert(sizeof(LeasePolicyPacket)==1072);
