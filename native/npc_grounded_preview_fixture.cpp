#include "npc_grounded_preview.h"
#include <cassert>
#include <cstdio>
#include <limits>
using namespace e33_npc_presentation;
struct Ops {
    e33_actor_pose::Pose pose{{0,0,200},{0,90,0}};
    bool valid=true,blocked=false,unknown=false,accepted=true,adjust=false,bad_readback=false;
    unsigned traces=0,teleports=0,miss=0;double spread=0,half=40,height=88,offset_z=0,normal_z=1,minimum_y=-1.e8;
    bool current(){return valid;}
    bool bounds(bool player,PreviewBounds& out){
        out={{player?0.:pose.location[0],player?0.:pose.location[1],player?200.:pose.location[2]+offset_z},
             {player?40.:half,40,player?88.:height}};
        if(bad_readback&&teleports)out.center[2]+=10;
        return true;
    }
    bool location(double (&out)[3]){for(unsigned i=0;i<3;++i)out[i]=pose.location[i];return true;}
    bool rotation(double (&out)[3]){for(unsigned i=0;i<3;++i)out[i]=pose.rotation[i];return true;}
    bool player_pose(e33_actor_pose::Pose& out){out={{0,0,200},{0,0,0}};return true;}
    e33_surface_query::Result surface(const double* start,const double*,e33_surface_query::Sample& out){
        ++traces;if(traces==miss||start[1]<minimum_y)return e33_surface_query::Result::NoHit;
        out={{0,0,100+spread*traces},{0,0,normal_z}};return e33_surface_query::Result::Hit;
    }
    e33_volume_query::Result volume(const double*,const double*){
        return blocked?e33_volume_query::Result::Blocked:e33_volume_query::Result::Clear;
    }
    bool teleport(const double (&to)[3],const double (&rot)[3],bool& success){
        ++teleports;for(unsigned i=0;i<3;++i){pose.location[i]=to[i];pose.rotation[i]=rot[i];}
        if(adjust)pose.location[0]+=1;
        success=accepted;return !unknown;
    }
};
int main(){
    {Ops o;GroundedPreview j;assert(place_preview(o,j,true)==PreviewPlacementResult::Complete);
     assert(j.samples==9&&j.support&&j.clearance&&!j.verified&&!j.placement.attempted&&o.teleports==0);
     assert(j.destination[0]==1600&&j.destination[2]==203&&o.pose.location[0]==0);}
    {Ops o;GroundedPreview j;assert(place_preview(o,j)==PreviewPlacementResult::Complete);
     assert(j.samples==9&&j.support&&j.clearance&&j.verified&&o.pose.rotation[1]==90);
     assert(o.pose.location[0]==1600&&o.pose.location[2]==203);
     assert(place_preview(o,j)==PreviewPlacementResult::AlreadyAttempted&&o.teleports==1);}
    {Ops o;GroundedPreview j;o.valid=false;assert(place_preview(o,j)==PreviewPlacementResult::Rejected&&o.traces==0&&o.teleports==0);}
    {Ops o;GroundedPreview j;o.half=std::numeric_limits<double>::quiet_NaN();assert(place_preview(o,j)==PreviewPlacementResult::Rejected&&o.teleports==0);}
    {Ops o;GroundedPreview j;o.half=-1;assert(place_preview(o,j)==PreviewPlacementResult::Rejected&&o.teleports==0);}
    {Ops o;GroundedPreview j;o.miss=5;assert(place_preview(o,j)==PreviewPlacementResult::Unsupported&&j.samples==4&&o.teleports==0);}
    {Ops o;GroundedPreview j;o.spread=20;assert(place_preview(o,j)==PreviewPlacementResult::Unsupported&&o.teleports==0);}
    {Ops o;GroundedPreview j;o.blocked=true;assert(place_preview(o,j)==PreviewPlacementResult::Blocked&&j.support&&!j.clearance&&o.teleports==0);}
    {Ops o;GroundedPreview j;o.unknown=true;assert(place_preview(o,j)==PreviewPlacementResult::PlacementFailed&&j.placement.attempted&&!j.placement.acknowledged);
     assert(place_preview(o,j)==PreviewPlacementResult::AlreadyAttempted&&o.teleports==1);}
    {Ops o;GroundedPreview j;o.accepted=false;assert(place_preview(o,j)==PreviewPlacementResult::PlacementFailed&&!j.verified);}
    {Ops o;GroundedPreview j;o.adjust=true;assert(place_preview(o,j)==PreviewPlacementResult::PlacementFailed&&!j.verified);}
    {Ops o;GroundedPreview j;o.bad_readback=true;assert(place_preview(o,j)==PreviewPlacementResult::PlacementFailed&&j.placement.readback&&!j.verified);}
    {Ops o;GroundedPreview j;o.half=759.5322875976562;o.height=974.1627960205078;o.offset_z=1032.4852752685547;
     assert(place_preview(o,j)==PreviewPlacementResult::Complete&&j.verified&&o.teleports==1);
     assert(std::abs(o.pose.location[2]+o.offset_z-o.height-115.)<1.e-8);
     assert(o.pose.location[0]>=1600.&&o.pose.rotation[1]==90);}
    {Ops o;GroundedPreview j;o.normal_z=.5;
     assert(place_preview(o,j)==PreviewPlacementResult::Unsupported&&!j.placement.attempted&&o.teleports==0);}
    {Ops o;GroundedPreview j;assert(place_preview(o,j,true,30.,800.)==PreviewPlacementResult::Complete&&!j.placement.attempted&&o.teleports==0);
     assert(std::abs(j.destination[0]-2400.*std::cos(3.14159265358979323846/6.))<1.e-8);
     assert(std::abs(j.destination[1]-1200.)<1.e-8);
     assert(place_preview(o,j,false,30.,800.)==PreviewPlacementResult::Complete&&j.verified&&o.teleports==1);}
    for(const auto p:{std::pair<double,double>{61.,0.},{0.,-1.},{0.,1601.},
            {std::numeric_limits<double>::quiet_NaN(),0.},{0.,std::numeric_limits<double>::infinity()}}){
        Ops o;GroundedPreview j;assert(place_preview(o,j,true,p.first,p.second)==PreviewPlacementResult::Rejected&&o.traces==0&&o.teleports==0);
    }
    {Ops o;GroundedPreview j;unsigned candidates=0;o.minimum_y=100.;
     assert(place_preview_nearby(o,j,candidates)==PreviewPlacementResult::Complete&&candidates==3&&o.teleports==1&&j.verified);
     assert(o.pose.location[1]>100.&&o.pose.rotation[1]==90);}
    {Ops o;GroundedPreview j;unsigned candidates=0;o.minimum_y=1.e8;
     assert(place_preview_nearby(o,j,candidates)==PreviewPlacementResult::Unsupported&&candidates==27&&o.teleports==0&&!j.placement.attempted);}
    {Ops o;GroundedPreview j;unsigned candidates=0;o.minimum_y=100.;o.unknown=true;
     assert(place_preview_nearby(o,j,candidates)==PreviewPlacementResult::PlacementFailed&&candidates==3&&o.teleports==1&&!j.placement.acknowledged);
     assert(place_preview_nearby(o,j,candidates)==PreviewPlacementResult::AlreadyAttempted&&o.teleports==1);}
    {Ops o;GroundedPreview j;unsigned candidates=0;o.valid=false;
     assert(place_preview_nearby(o,j,candidates)==PreviewPlacementResult::Rejected&&candidates==1&&o.teleports==0&&o.traces==0);}
    std::puts("Shared grounded preview: 20 scenarios passed, including bounded read-only search and no placement replay");
}
