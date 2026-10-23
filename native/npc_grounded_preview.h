#pragma once
#include "actor_pose_operations.h"
#include "surface_query.h"
#include "volume_query.h"
#include "enemy_ground_search.h"
#include <algorithm>

namespace e33_npc_presentation {
struct PreviewBounds {double center[3]{},half[3]{};};
struct GroundedPreview {
    e33_actor_pose::Placement placement{};
    double minimum=0,maximum=0,destination[3]{};
    unsigned samples=0;
    bool support=false,clearance=false,verified=false;
    bool at_construction=false;
};
enum class PreviewPlacementResult {Complete,Rejected,Unsupported,Blocked,PlacementFailed,AlreadyAttempted};

// Clea's held original assembly stays hidden, nonblocking and movement-disabled.
// This policy uses the existing SDK queries and pose journal. It does not enable
// actor/component ticks, invoke NPC actions, or replace authored component poses.
template<class Ops>
PreviewPlacementResult place_preview(Ops& ops,GroundedPreview& journal,bool plan_only=false,
        double heading_offset_degrees=0.,double extra_distance=0.){
    if(journal.placement.attempted)return PreviewPlacementResult::AlreadyAttempted;
    if(!std::isfinite(heading_offset_degrees)||std::abs(heading_offset_degrees)>60.||
       !std::isfinite(extra_distance)||extra_distance<0.||extra_distance>1600.)return PreviewPlacementResult::Rejected;
    journal=GroundedPreview{};
    PreviewBounds actor{},player{};e33_actor_pose::Pose pose{},player_pose{};
    if(!ops.current()||!ops.bounds(false,actor)||!ops.bounds(true,player)||
       !e33_actor_pose::observe(ops,pose)||!ops.player_pose(player_pose))return PreviewPlacementResult::Rejected;
    for(const auto* bounds:{&actor,&player})for(unsigned i=0;i<3;++i)
        if(!std::isfinite(bounds->center[i])||std::abs(bounds->center[i])>1.e7||
           !std::isfinite(bounds->half[i])||bounds->half[i]<=0||bounds->half[i]>1.e5)
            return PreviewPlacementResult::Rejected;
    if(!e33_actor_pose::finite(player_pose.location)||!e33_actor_pose::finite(player_pose.rotation))
        return PreviewPlacementResult::Rejected;
    const auto distance=std::max(1600.,std::hypot(actor.half[0],actor.half[1])+
        std::hypot(player.half[0],player.half[1])+500.)+extra_distance;
    if(distance>200000.)return PreviewPlacementResult::Rejected;
    const auto yaw=(std::remainder(player_pose.rotation[1],360.)+heading_offset_degrees)*3.14159265358979323846/180.;
    const double xy[]={player.center[0]+std::cos(yaw)*distance,player.center[1]+std::sin(yaw)*distance};
    journal.minimum=1.e8;journal.maximum=-1.e8;
    for(int y=-1;y<=1;++y)for(int x=-1;x<=1;++x){
        const double start[]={xy[0]+x*actor.half[0],xy[1]+y*actor.half[1],player.center[2]+5000.};
        const double end[]={start[0],start[1],player.center[2]-10000.};
        e33_surface_query::Sample sample{};
        if(!ops.current()||ops.surface(start,end,sample)!=e33_surface_query::Result::Hit)
            return PreviewPlacementResult::Unsupported;
        if(!e33_actor_pose::finite(sample.point)||!e33_actor_pose::finite(sample.normal)||sample.normal[2]<.75)
            return PreviewPlacementResult::Unsupported;
        journal.minimum=std::min(journal.minimum,sample.point[2]);
        journal.maximum=std::max(journal.maximum,sample.point[2]);++journal.samples;
    }
    if(journal.maximum-journal.minimum>100.)return PreviewPlacementResult::Unsupported;
    journal.support=true;
    const double center[]={xy[0],xy[1],journal.maximum+actor.half[2]+15.};
    if(!ops.current()||ops.volume(center,actor.half)!=e33_volume_query::Result::Clear)
        return PreviewPlacementResult::Blocked;
    journal.clearance=true;
    for(unsigned i=0;i<3;++i)journal.destination[i]=pose.location[i]+center[i]-actor.center[i];
    if(plan_only){journal.placement.before=pose;return PreviewPlacementResult::Complete;}
    // Existing durable SDK operation handles uncertain dispatch and preserves
    // the original rotation. Never retry an attempted teleport or overwrite it.
    if(e33_actor_pose::place_preserving_rotation(ops,journal.destination,200000.,.1,journal.placement)!=
       e33_actor_pose::Result::Placed)return PreviewPlacementResult::PlacementFailed;
    PreviewBounds checked{};
    if(!ops.current()||!ops.bounds(false,checked))return PreviewPlacementResult::PlacementFailed;
    for(unsigned i=0;i<3;++i)if(!std::isfinite(checked.center[i])||std::abs(checked.center[i]-center[i])>.1)
        return PreviewPlacementResult::PlacementFailed;
    journal.verified=true;return PreviewPlacementResult::Complete;
}

// Probe at most 27 positions in the original forward 120-degree sector, then
// revalidate and place ONCE. Only unsupported/blocked read-only plans may advance
// the search. A stale context, rejected getter or any placement attempt stops it.
// Existing NPC consumers retain the unchanged single-position default above.
template<class Ops>
PreviewPlacementResult place_preview_nearby(Ops& ops,GroundedPreview& journal,unsigned& candidates){
    if(journal.placement.attempted)return PreviewPlacementResult::AlreadyAttempted;
    candidates=0;
    auto result=PreviewPlacementResult::Rejected;
    for(const double extra:{0.,800.,1600.})for(const auto degrees:e33_enemy_ground::heading_offsets){
        ++candidates;result=place_preview(ops,journal,true,degrees,extra);
        if(result==PreviewPlacementResult::Complete)return place_preview(ops,journal,false,degrees,extra);
        if(result!=PreviewPlacementResult::Unsupported&&result!=PreviewPlacementResult::Blocked)return result;
    }
    return result;
}
}
