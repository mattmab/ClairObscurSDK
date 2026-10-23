#pragma once
#include "actor_pose_operations.h"

namespace e33_enemy_combat {
// K2_TeleportTo can raise a capsule for collision clearance. Accept only a
// small upward correction; horizontal displacement and rotation remain strict.
inline bool collision_lift(const e33_actor_pose::Placement& pose,const double (&requested)[3]) {
    if(!pose.acknowledged||!pose.engine_accepted||!pose.readback||
       !e33_actor_pose::finite(requested)||!e33_actor_pose::finite(pose.after.location)||
       !e33_actor_pose::same_rotation(pose.before.rotation,pose.after.rotation,1.e-3))return false;
    const auto dx=pose.after.location[0]-requested[0],dy=pose.after.location[1]-requested[1];
    const auto dz=pose.after.location[2]-requested[2];
    return std::hypot(dx,dy)<=1.&&dz>=-1.&&dz<=20.&&
        std::sqrt(e33_actor_pose::distance_squared(pose.before.location,pose.after.location))<=2020.;
}
}
