#pragma once
#include <cmath>

namespace e33_actor_pose {
struct Pose { double location[3]{},rotation[3]{}; };
enum class Result {
    Placed, Adjusted, InvalidInput, ObservationRejected, AlreadyAttempted,
    DispatchUnknown, EngineRejected, ReadbackRejected
};
struct Placement {
    Pose before{},after{};
    bool attempted=false,acknowledged=false,engine_accepted=false,readback=false;
};

inline bool finite(const double (&values)[3]) {
    for(double value:values)if(!std::isfinite(value))return false;
    return true;
}
inline double distance_squared(const double (&a)[3],const double (&b)[3]) {
    double result=0;
    for(unsigned i=0;i<3;++i){const auto delta=a[i]-b[i];result+=delta*delta;}
    return result;
}
inline bool same_rotation(const double (&a)[3],const double (&b)[3],double tolerance) {
    if(!finite(a)||!finite(b)||!std::isfinite(tolerance)||tolerance<0)return false;
    for(unsigned i=0;i<3;++i)
        if(std::abs(std::remainder(std::remainder(a[i],360.)-
                                 std::remainder(b[i],360.),360.))>tolerance)return false;
    return true;
}

// Ops binds one exact actor identity, world, authority and game-thread context.
// Its getters and teleport must independently validate those before dispatch.
// teleport binds one preselected canonical operation (engine_profiles.h):
// Actor.K2_TeleportTo, or K2_SetActorLocationAndRotation with teleport physics
// after the consumer has separately verified support/clearance. Never switch
// backends or retry after a dispatch attempt. Existing consumers are unchanged.
// reports dispatch acknowledgement separately from its engine bool return, and
// must not retry an uncertain call. These helpers neither acquire ownership nor
// prove ground support, navigation, assembly clearance or attachment suitability.
template<class Ops> bool observe(Ops& ops,Pose& pose) {
    Pose observed{};
    if(!ops.current()||!ops.location(observed.location)||
       !ops.rotation(observed.rotation)||!ops.current()||
       !finite(observed.location)||!finite(observed.rotation))return false;
    pose=observed;return true;
}

// Journal belongs to the consumer's durable transaction. Preserve it on every
// failure. A subsequent request needs fresh policy/ownership checks; it must not
// clear an unknown dispatch or silently restore a pose over an external edit.
template<class Ops>
Result place_preserving_rotation(Ops& ops,const double (&destination)[3],
        double maximum_distance,double tolerance,Placement& journal) {
    if(journal.attempted)return Result::AlreadyAttempted;
    if(!finite(destination)||!std::isfinite(maximum_distance)||maximum_distance<=0||
       !std::isfinite(tolerance)||tolerance<0||tolerance>maximum_distance)
        return Result::InvalidInput;
    if(!observe(ops,journal.before))return Result::ObservationRejected;
    if(std::sqrt(distance_squared(destination,journal.before.location))>maximum_distance)
        return Result::InvalidInput;
    if(!ops.current())return Result::ObservationRejected;
    journal.attempted=true;
    if(!ops.teleport(destination,journal.before.rotation,journal.engine_accepted))
        return Result::DispatchUnknown;
    journal.acknowledged=true;
    if(!journal.engine_accepted)return Result::EngineRejected;
    if(!observe(ops,journal.after))return Result::ReadbackRejected;
    journal.readback=true;
    if(std::sqrt(distance_squared(destination,journal.after.location))>tolerance||
       !same_rotation(journal.before.rotation,journal.after.rotation,1.e-3))
        return Result::Adjusted;
    return Result::Placed;
}
}
