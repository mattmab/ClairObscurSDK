#pragma once
#include <cmath>
#include <cstdint>
#include <cstring>
// Copied-value BoxTraceSingle adapter. Invoke validates exact engine profile,
// context and identities on each call. Opaque HitResult stays inside the frame.
namespace e33_volume_query {
enum class Result {Clear,Blocked,Rejected,Invalid};
struct IgnoredActors {const uint64_t* data;int32_t num,max;};
static_assert(sizeof(IgnoredActors)==16,"engine array extent");
template<class Invoke>
Result sample(Invoke&& invoke,uint64_t context,const double* center,const double* half,
              const uint64_t* ignored,int32_t count){
    if(!context||!center||!half||count<0||count>64||(count&&!ignored))return Result::Invalid;
    for(unsigned i=0;i<3;++i)if(!std::isfinite(center[i])||std::abs(center[i])>1.e8||
        !std::isfinite(half[i])||half[i]<=0||half[i]>1.e5)return Result::Invalid;
    for(int32_t i=0;i<count;++i)if(!ignored[i])return Result::Invalid;
    alignas(16) uint8_t frame[464]{};
    std::memcpy(frame,&context,8);std::memcpy(frame+8,center,24);std::memcpy(frame+32,center,24);
    std::memcpy(frame+56,half,24);
    const IgnoredActors actors{ignored,count,count};std::memcpy(frame+112,&actors,16);
    frame[384]=1; // IgnoreSelf; visibility trace channel 0, no debug drawing.
    if(!invoke(frame))return Result::Rejected;
    if(frame[424]>1)return Result::Invalid;
    return frame[424]?Result::Blocked:Result::Clear;
}
}
