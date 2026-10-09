#pragma once
#include "invocation_protocol.h"

// Caller owns a registered strong reference and runs on the game thread.
// Zero is an observed unassigned serial, never an identity wildcard.
template<class Ops>
bool stabilize_retained_identity(Ops& ops,CallIdentity& identity) {
    if(identity.index<0 || !identity.address || identity.serial<0 || !ops.can_assign()) return false;
    auto same=[](const CallIdentity& a,const CallIdentity& b) {
        return a.index==b.index && a.serial==b.serial && a.address==b.address;
    };
    if(!same(ops.capture(identity.address),identity)) return false;
    if(identity.serial>0) return true;
    const auto serial=ops.allocate_serial(identity.index);
    auto observed=ops.capture(identity.address);
    if(serial<1001 || observed.index!=identity.index || observed.address!=identity.address ||
       observed.serial!=serial || !ops.can_assign()) return false;
    identity=observed;
    return true;
}
