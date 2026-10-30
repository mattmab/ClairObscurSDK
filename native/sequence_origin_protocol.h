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

// A separately negotiated complete transform, expressed as a translation and
// bounded yaw in degrees. Quaternion values are computed in the runtime; the
// client cannot supply arbitrary rotation, scale, or object addresses.
#pragma pack(push,1)
struct SequenceOriginTransformPacket {
    uint32_t magic,version;
    double x,y,z,yaw;
};
#pragma pack(pop)
static_assert(sizeof(SequenceOriginTransformPacket)==40);
inline bool sequence_origin_transform_packet(const SequenceOriginTransformPacket& p) {
    return p.magic==0x54533345 && p.version==1 &&
        std::isfinite(p.x) && std::isfinite(p.y) && std::isfinite(p.z) &&
        std::isfinite(p.yaw) && std::abs(p.x)<=1e7 && std::abs(p.y)<=1e7 &&
        std::abs(p.z)<=1e7 && std::abs(p.yaw)<=180.;
}
inline void sequence_origin_transform_quaternion(const SequenceOriginTransformPacket& p,double* q) {
    constexpr double radians_per_degree=0.017453292519943295769236907684886;
    const auto half=p.yaw*radians_per_degree/2.;
    q[0]=0.;q[1]=0.;q[2]=std::sin(half);q[3]=std::cos(half);
}
