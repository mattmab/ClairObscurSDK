#pragma once
#include <cmath>
#include <cstdint>
#include <cstring>

// Shared copied-value adapter for validated LineTraceSingle/BreakHitResult
// profiles. Invoke must validate the engine identities/schema on every call.
// HitResult never crosses the SDK wire or enters the reflection value codec.
namespace e33_surface_query {
enum class Result { Hit, NoHit, Rejected, Invalid };
struct Sample { double point[3]{},normal[3]{}; };
struct IgnoredActors { const uint64_t* data;int32_t num,max; };
static_assert(sizeof(IgnoredActors)==16,"Engine array layout");

template<class Invoke>
Result sample(Invoke&& invoke,uint64_t context,const double* start,const double* end,
              const uint64_t* ignored,int32_t count,Sample& output) {
    output={};
    if(!context||!start||!end||count<0||count>64||(count&&!ignored))return Result::Invalid;
    for(int i=0;i<3;++i)if(!std::isfinite(start[i])||!std::isfinite(end[i])||
        std::abs(start[i])>1.e8||std::abs(end[i])>1.e8)return Result::Invalid;
    for(int i=0;i<count;++i)if(!ignored[i])return Result::Invalid;
    alignas(16) uint8_t args[464]{};
    std::memcpy(args,&context,8);std::memcpy(args+8,start,24);std::memcpy(args+32,end,24);
    const IgnoredActors actors{ignored,count,count};std::memcpy(args+64,&actors,16);args[336]=1;
    if(!invoke(0,args))return Result::Rejected;
    if(!args[376])return Result::NoHit;
    uint8_t hit[248];std::memcpy(hit,args+88,248);std::memset(args,0,sizeof(args));std::memcpy(args,hit,248);
    if(!invoke(1,args))return Result::Rejected;
    if(!args[248]||args[249])return Result::NoHit;
    Sample candidate{};std::memcpy(candidate.point,args+288,24);std::memcpy(candidate.normal,args+336,24);
    for(int i=0;i<3;++i)if(!std::isfinite(candidate.point[i])||!std::isfinite(candidate.normal[i])||
        std::abs(candidate.point[i])>1.e8)return Result::Invalid;
    if(candidate.normal[2]<.75)return Result::NoHit;
    output=candidate;return Result::Hit;
}
}
