#include "actor_pose_operations.h"
#include "enemy_combat_placement_policy.h"
#include <cassert>
#include <cstdio>
#include <limits>

using namespace e33_actor_pose;
struct Ops {
    Pose pose{{1,2,3},{0,180,0}};
    bool valid=true,dispatch=true,accepted=true,readable=true,adjust=false,throw_after=false,rotate=false;
    unsigned calls=0,checks=0,invalidate_at=0;
    bool current(){return valid&&(!invalidate_at||++checks<invalidate_at);}
    bool location(double (&out)[3]){if(!readable)return false;for(unsigned i=0;i<3;++i)out[i]=pose.location[i];return true;}
    bool rotation(double (&out)[3]){for(unsigned i=0;i<3;++i)out[i]=pose.rotation[i];return true;}
    bool teleport(const double (&location)[3],const double (&rotation)[3],bool& success){
        ++calls;
        for(unsigned i=0;i<3;++i){pose.location[i]=location[i];pose.rotation[i]=rotation[i];}
        pose.rotation[1]=-180; // Unreal can normalize the equivalent rotation.
        if(rotate)pose.rotation[1]=-170;
        if(adjust)pose.location[0]+=20;
        if(throw_after)throw 1;
        success=accepted;
        if(!dispatch)return false;
        return true;
    }
};
int main(){
    const double destination[3]={101,2,3};
    {Ops ops;Placement journal;assert(place_preserving_rotation(ops,destination,200,0.01,journal)==Result::Placed);
     assert(journal.attempted&&journal.acknowledged&&journal.engine_accepted&&journal.readback);
     assert(journal.before.location[0]==1&&journal.after.location[0]==101);
     assert(place_preserving_rotation(ops,destination,200,0.01,journal)==Result::AlreadyAttempted&&ops.calls==1);}
    {Ops ops;Placement journal;ops.adjust=true;
     assert(place_preserving_rotation(ops,destination,200,0.01,journal)==Result::Adjusted&&journal.after.location[0]==121);}
    {Ops ops;Placement journal;ops.rotate=true;
     assert(place_preserving_rotation(ops,destination,200,0.01,journal)==Result::Adjusted);}
    {Ops ops;Placement journal;ops.pose.rotation[0]=std::numeric_limits<double>::quiet_NaN();
     assert(place_preserving_rotation(ops,destination,200,0.01,journal)==Result::ObservationRejected&&ops.calls==0);}
    {Ops ops;Placement journal;ops.dispatch=false;
     assert(place_preserving_rotation(ops,destination,200,0.01,journal)==Result::DispatchUnknown);
     assert(journal.attempted&&!journal.acknowledged);
     assert(place_preserving_rotation(ops,destination,200,0.01,journal)==Result::AlreadyAttempted&&ops.calls==1);}
    {Ops ops;Placement journal;ops.accepted=false;
     assert(place_preserving_rotation(ops,destination,200,0.01,journal)==Result::EngineRejected&&journal.acknowledged&&!journal.readback);}
    {Ops ops;Placement journal;ops.readable=false;
     assert(place_preserving_rotation(ops,destination,200,0.01,journal)==Result::ObservationRejected&&ops.calls==0);}
    {Ops ops;Placement journal;ops.invalidate_at=3;
     assert(place_preserving_rotation(ops,destination,200,0.01,journal)==Result::ObservationRejected&&!journal.attempted&&ops.calls==0);}
    {Ops ops;Placement journal;ops.invalidate_at=4;
     assert(place_preserving_rotation(ops,destination,200,0.01,journal)==Result::ReadbackRejected&&journal.acknowledged&&!journal.readback);}
    {Ops ops;Placement journal;const double bad[3]={std::numeric_limits<double>::quiet_NaN(),0,0};
     assert(place_preserving_rotation(ops,bad,200,0.01,journal)==Result::InvalidInput&&ops.calls==0);}
    {Ops ops;Placement journal;assert(place_preserving_rotation(ops,destination,50,0.01,journal)==Result::InvalidInput&&!journal.attempted&&ops.calls==0);}
    {Ops ops;Placement journal;assert(place_preserving_rotation(ops,destination,200,-1,journal)==Result::InvalidInput&&ops.calls==0);}
    {Ops ops;Placement journal;ops.throw_after=true;
     try{place_preserving_rotation(ops,destination,200,0.01,journal);assert(false);}catch(int){}
     assert(journal.attempted&&!journal.acknowledged);
     assert(place_preserving_rotation(ops,destination,200,0.01,journal)==Result::AlreadyAttempted&&ops.calls==1);}
    {Placement pose;pose.acknowledged=pose.engine_accepted=pose.readback=true;
     for(unsigned i=0;i<3;++i)pose.after.location[i]=destination[i];
     pose.after.location[2]+=5.25;assert(e33_enemy_combat::collision_lift(pose,destination));
     pose.after.location[2]=destination[2]+20;assert(e33_enemy_combat::collision_lift(pose,destination));
     pose.after.location[2]+=0.01;assert(!e33_enemy_combat::collision_lift(pose,destination));
     pose.after.location[2]=destination[2]-1.01;assert(!e33_enemy_combat::collision_lift(pose,destination));
     pose.after.location[2]=destination[2];pose.after.location[0]+=2;
     assert(!e33_enemy_combat::collision_lift(pose,destination));
     pose.after.location[0]=destination[0];pose.after.rotation[1]=10;
     assert(!e33_enemy_combat::collision_lift(pose,destination));
     pose.after.rotation[1]=0;pose.readback=false;assert(!e33_enemy_combat::collision_lift(pose,destination));}
    std::puts("Actor pose operations: 13 scenarios and 7 combat collision policy checks passed");
}
