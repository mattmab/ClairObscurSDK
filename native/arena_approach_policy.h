#pragma once
#include "surface_query.h"
#include "volume_query.h"
#include <algorithm>
#include <cmath>

namespace e33_arena_approach {
inline constexpr double distances[]={1600.,2400.,3200.};
enum class Result {Supported,Unsupported,Rejected};
inline bool permits_placement(Result route,bool required){
    // Advisory route observations never make a rejected/stale query valid.
    return route==Result::Supported||(!required&&route==Result::Unsupported);
}
enum class Reason : uint32_t {NotRun,Supported,Input,SurfaceRejected,NoSurface,
    Slope,Step,StartHeight,WidthHeight,TotalHeight,ClearanceRejected,Blocked,EndHeight};
struct Diagnostic {
    uint32_t reason=0,step=0;int32_t lane=0;uint32_t reserved=0;
    double position[3]{},observed=0,reference=0;
};
static_assert(sizeof(Diagnostic)==56,"copied corridor diagnostic");

// Keep the actual encounter anchor on the player's forward line. A rigid
// translation preserves all original helper/arena/slot/focus relationships.
inline bool origin(const double* pawn,double yaw,double distance,
        const double* anchor_offset,double* result){
    if(!pawn||!anchor_offset||!result||!std::isfinite(yaw)||
       !std::isfinite(distance)||distance<1600.||distance>3200.)return false;
    for(unsigned i=0;i<2;++i)if(!std::isfinite(pawn[i])||!std::isfinite(anchor_offset[i]))return false;
    const double angle=std::remainder(yaw,360.)*3.14159265358979323846/180.;
    result[0]=pawn[0]+std::cos(angle)*distance-anchor_offset[0];
    result[1]=pawn[1]+std::sin(angle)*distance-anchor_offset[1];
    return true;
}

// Bounded geometric screening, not a navmesh/pathfinding guarantee. The same
// SDK surface and volume operations are supplied by the owned arena consumer.
// Three lanes cover the observed pawn footprint at <=25cm intervals. Reject
// holes, sharp steps, steep sampled surfaces and obstructed body clearance.
// No actor mutation is performed here; a refusal leaves staging hidden.
template<class Ops>
Result corridor(Ops& ops,const double* pawn,const double* target,const double* half,
        double target_floor,unsigned& samples,Diagnostic* diagnostic=nullptr){
    samples=0;
    if(diagnostic)*diagnostic={};
    auto finish=[&](Result result,Reason reason,double observed=0.,double reference=0.){
        if(diagnostic){diagnostic->reason=static_cast<uint32_t>(reason);
            diagnostic->observed=std::isfinite(observed)?observed:0.;
            diagnostic->reference=std::isfinite(reference)?reference:0.;}
        return result;
    };
    if(!pawn||!target||!half)return finish(Result::Rejected,Reason::Input);
    for(unsigned i=0;i<3;++i)if(!std::isfinite(pawn[i])||!std::isfinite(target[i])||
        !std::isfinite(half[i])||half[i]<=0||half[i]>1000)return finish(Result::Rejected,Reason::Input);
    if(!std::isfinite(target_floor))return finish(Result::Rejected,Reason::Input);
    const double dx=target[0]-pawn[0],dy=target[1]-pawn[1],length=std::hypot(dx,dy);
    if(length<1500.||length>3300.)return finish(Result::Rejected,Reason::Input);
    const double radius=std::hypot(half[0],half[1]);
    const unsigned steps=static_cast<unsigned>(std::ceil(length/25.));
    const double lateral[]={-dy/length*radius,dx/length*radius};
    double previous[3]{},baseline=0;
    for(unsigned i=0;i<=steps;++i){
        const double t=static_cast<double>(i)/steps;
        double low=1.e8,high=-1.e8;
        for(int lane=-1;lane<=1;++lane){
            const double start[]={pawn[0]+dx*t+lane*lateral[0],pawn[1]+dy*t+lane*lateral[1],
                i?baseline+150.:pawn[2]};
            const double end[]={start[0],start[1],i?baseline-150.:pawn[2]-2*half[2]-100.};
            if(diagnostic){diagnostic->step=i;diagnostic->lane=lane;
                std::copy(start,start+3,diagnostic->position);}
            e33_surface_query::Sample sample{};++samples;
            const auto result=ops.surface(start,end,sample);
            if(result==e33_surface_query::Result::Rejected||result==e33_surface_query::Result::Invalid)return finish(Result::Rejected,Reason::SurfaceRejected);
            if(result!=e33_surface_query::Result::Hit)return finish(Result::Unsupported,Reason::NoSurface);
            if(!std::isfinite(sample.point[2])||!std::isfinite(sample.normal[2]))return finish(Result::Rejected,Reason::SurfaceRejected);
            if(sample.normal[2]<.75)return finish(Result::Unsupported,Reason::Slope,sample.normal[2],.75);
            if(i&&std::abs(sample.point[2]-previous[lane+1])>25.)return finish(Result::Unsupported,Reason::Step,sample.point[2],previous[lane+1]);
            previous[lane+1]=sample.point[2];low=std::min(low,sample.point[2]);high=std::max(high,sample.point[2]);
        }
        if(!i){
            baseline=previous[1];
            if(std::abs(baseline-(pawn[2]-half[2]))>100.)return finish(Result::Unsupported,Reason::StartHeight,baseline,pawn[2]-half[2]);
        }
        if(high-low>100.)return finish(Result::Unsupported,Reason::WidthHeight,high,low);
        if(std::abs(low-baseline)>100.||std::abs(high-baseline)>100.)
            return finish(Result::Unsupported,Reason::TotalHeight,std::abs(low-baseline)>100.?low:high,baseline);
        const double center[]={pawn[0]+dx*t,pawn[1]+dy*t,high+half[2]+15.};
        if(diagnostic){diagnostic->lane=0;std::copy(center,center+3,diagnostic->position);}
        const auto clearance=ops.volume(center,half);
        if(clearance==e33_volume_query::Result::Rejected||clearance==e33_volume_query::Result::Invalid)return finish(Result::Rejected,Reason::ClearanceRejected);
        if(clearance!=e33_volume_query::Result::Clear)return finish(Result::Unsupported,Reason::Blocked);
    }
    return std::abs(previous[1]-target_floor)<=100.?
        finish(Result::Supported,Reason::Supported,previous[1],target_floor):
        finish(Result::Unsupported,Reason::EndHeight,previous[1],target_floor);
}
}
