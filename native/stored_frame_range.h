#pragma once
#include <cstdint>
#include <cstring>
#include <stdexcept>

// Exact executable 218a2478...: UMovieSceneSequencePlayer initialization
// 142d5387a copies MovieScene.PlaybackRange (+108, 16 bytes). Lower kind/value
// occupy +0/+4; upper +8/+c. 142d538a4 and 142d538c1 apply the (0,1) tables
// at 1472b7da8/1472b7db0: exclusive lower increments, inclusive upper increments.
// UMovieSceneSection 142d51a00/142d51a32 skips each endpoint when kind==2.
// Padding and the unused numeric payload of an open endpoint are never emitted.
struct StoredFrameRangeCopy { uint8_t lower_kind,upper_kind;int32_t lower,upper; };
inline StoredFrameRangeCopy copy_stored_frame_range(const uint8_t* bytes,size_t width) {
    if(!bytes || width!=16)throw std::runtime_error("FRAME_RANGE_SIZE_INVALID");
    StoredFrameRangeCopy result{bytes[0],bytes[8],0,0};
    if(result.lower_kind>2 || result.upper_kind>2)throw std::runtime_error("FRAME_RANGE_KIND_INVALID");
    if(result.lower_kind!=2)std::memcpy(&result.lower,bytes+4,4);
    if(result.upper_kind!=2)std::memcpy(&result.upper,bytes+12,4);
    return result;
}
