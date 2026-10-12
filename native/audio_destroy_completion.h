#pragma once
#include "invocation_protocol.h"
// Recognize only the already-completed, exact owned AudioComponent destruction
// reached after a returned Stop. Never reinterpret arbitrary202 as success.
struct AudioDestroyMarkers {
    uint32_t object_flags=0,item_flags=0;
    uint8_t component_flags=0,activity_flags=0;
};
template<class Ops>
bool completed_audio_destruction(Ops& ops,uint32_t state,uint32_t step,uint32_t error,
                                 uint32_t outcome,uint32_t detail,uint64_t session,uint64_t token,
                                 const CallIdentity& identity) {
    if(state!=2 || step!=1 || error!=202 || outcome!=CallNotDispatched || detail!=0x20200007u ||
       !session || !token || identity.index<0 || identity.serial<=0 || !identity.address ||
       !ops.context() || !ops.owns(session,token,identity.address) || !ops.matches(identity) ||
       !ops.exact_class(identity)) return false;
    const auto markers=ops.markers(identity);
    return (markers.object_flags&0x40000000u) && (markers.item_flags&0x200000u) &&
        (markers.component_flags&0x20u) && !(markers.activity_flags&8u) &&
        ops.matches(identity) && ops.owns(session,token,identity.address);
}
