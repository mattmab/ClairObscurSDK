#pragma once
#include "invocation_protocol.h"
#include <limits>

// Only the SDK-owned sequence player can consume this request. The engine's
// FString-bearing playback parameters are constructed locally, never supplied
// by a controller. Frame units are the owned player's qualified frame rate.
#pragma pack(push,1)
struct SequenceSeekPacket {
    uint32_t magic,version;
    CallIdentity function;
    int32_t frame;
    float subframe;
    uint32_t outcome;
    uint32_t reserved[7];
};
#pragma pack(pop)
static_assert(sizeof(SequenceSeekPacket)==64);
inline bool sequence_seek_request(const SequenceSeekPacket& p) {
    if(p.magic!=0x53533345 || p.version!=1 || p.function.index<0 ||
       p.function.serial<=0 || !p.function.address || p.outcome ||
       !std::isfinite(p.subframe) || p.subframe<0 || p.subframe>=1) return false;
    for(const auto value:p.reserved) if(value) return false;
    return true;
}
inline bool sequence_seek_range(const SequenceSeekPacket& p,int32_t start,int32_t duration) {
    if(!sequence_seek_request(p) || duration<=0) return false;
    const auto end=int64_t(start)+duration;
    return end<=std::numeric_limits<int32_t>::max() &&
        p.frame>=start && p.frame<=end && (p.frame!=end || p.subframe==0);
}

// Layout qualified against MovieSceneSequencePlaybackParams on the supported
// executable. MarkedFrame stays an empty FString; no engine allocation escapes.
inline void sequence_seek_parameters(const SequenceSeekPacket& p,uint8_t (&bytes)[56]) {
    std::memset(bytes,0,sizeof(bytes));
    std::memcpy(bytes,&p.frame,4);std::memcpy(bytes+4,&p.subframe,4);
    bytes[52]=0; // EMovieScenePositionType::Frame
    bytes[53]=2; // EUpdatePositionMethod::Scrub
    bytes[54]=1; // bHasJumped
}
