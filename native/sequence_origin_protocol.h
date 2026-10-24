#pragma once
#include <cmath>
#include <cstdint>

// A copied translation only. No caller-supplied object, address, transform
// layout, property offset, scale, or rotation enters this protocol.
#pragma pack(push,1)
struct SequenceOriginPacket {
    uint32_t magic,version;
    double x,y,z;
};
#pragma pack(pop)
static_assert(sizeof(SequenceOriginPacket)==32);
inline bool sequence_origin_packet(const SequenceOriginPacket& p) {
    return p.magic==0x4f533345 && p.version==1 &&
        std::isfinite(p.x) && std::isfinite(p.y) && std::isfinite(p.z) &&
        std::abs(p.x)<=1e7 && std::abs(p.y)<=1e7 && std::abs(p.z)<=1e7;
}
