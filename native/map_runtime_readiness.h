#pragma once
#include "surface_query.h"
#include "engine_profile_types.h"
#include <algorithm>

// Read-only broadphase evidence. A hit must be close to the held pawn's feet;
// distant ground is not evidence that releasing the loading guard is safe.
// Invoke validates the fixed LineTraceSingle / BreakHitResult profiles each time.
// Owned accepts copied actor/component pointers only during this GT callback.
namespace e33_map_readiness {
inline const MeshField rendered_fields[]={
{"Tolerance","FloatProperty",0,4,0x18001040000280ULL,0x6e11560ULL,"","",0,"",0U,""},
{"ReturnValue","BoolProperty",4,1,0x18001040000780ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshFunction rendered={"PrimitiveComponent","WasRecentlyRendered",0x54020403,5,8,4,0x32cf640,rendered_fields,2};
inline const MeshField streaming_fields[]={
{"ReturnValue","BoolProperty",0,1,0x18001040000780ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshFunction streaming={"LevelStreaming","IsStreamingStatePending",0x54020403,1,1,0,0x38b2ad0,streaming_fields,1};
struct Support {uint32_t samples=0,hits=0,owned=0;double heights[5]{};};
template<class Invoke,class Owned>
bool support(Invoke&& invoke,Owned&& owned,uint64_t pawn,const double* center,
             double radius,double half_height,Support& output){
    output={};
    if(!pawn||!center||!std::isfinite(radius)||!std::isfinite(half_height)||
       radius<=0||radius>10000||half_height<radius||half_height>10000)return false;
    for(unsigned i=0;i<3;++i)if(!std::isfinite(center[i])||std::abs(center[i])>1.e8)return false;
    const double offsets[5][2]={{0,0},{.4,0},{-.4,0},{0,.4},{0,-.4}};
    for(unsigned i=0;i<5;++i){
        alignas(16) uint8_t args[464]{};
        const double start[]={center[0]+offsets[i][0]*radius,center[1]+offsets[i][1]*radius,center[2]-half_height+20.};
        const double end[]={start[0],start[1],center[2]-half_height-60.};
        std::memcpy(args,&pawn,8);std::memcpy(args+8,start,24);std::memcpy(args+32,end,24);
        const e33_surface_query::IgnoredActors ignored{&pawn,1,1};std::memcpy(args+64,&ignored,16);args[336]=1;
        ++output.samples;
        if(!invoke(0,args))return false;
        if(!args[376])continue;
        uint8_t hit[248];std::memcpy(hit,args+88,248);std::memset(args,0,sizeof(args));std::memcpy(args,hit,248);
        if(!invoke(1,args))return false;
        if(!args[248]||args[249])continue;
        double point[3]{},normal[3]{};std::memcpy(point,args+288,24);std::memcpy(normal,args+336,24);
        bool valid=true;for(unsigned k=0;k<3;++k)valid=valid&&std::isfinite(point[k])&&std::isfinite(normal[k])&&std::abs(point[k])<=1.e8;
        if(!valid)return false;
        if(normal[2]<.75||point[2]>start[2]+.01||point[2]<end[2]-.01)continue;
        uint64_t actor=0,component=0;std::memcpy(&actor,args+368,8);std::memcpy(&component,args+376,8);
        if(!actor||!component)return false;
        ++output.hits;output.heights[i]=point[2];if(owned(actor,component))++output.owned;
    }
    return true;
}
}
