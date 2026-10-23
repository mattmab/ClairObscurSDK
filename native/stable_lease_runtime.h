#pragma once
#include "lease_protocol.h"
#include "stable_identity.h"
#include "strong_lease_pool.h"

// Exact observed identity; caller runs under the ordinary lease GT/GC gate.
// This owns a runtime object in its mod scope, never in the metadata owner.
template<class Ops,class Pool>
void stable_lease_acquire(LeasePacket& lease,Ops& ops,Pool& pool,uint64_t session) {
        if(lease.version!=kLeaseVersion || lease.error || lease.outcome || lease.active ||
           lease.token || lease.object.index<0 || lease.object.serial<0 || !lease.object.address) {
            lease.error=411;lease.outcome=LeaseNotDispatched;return;
        }
        if(!ops.can_assign() || !ops.can_create(lease.object.address)) {
            lease.error=402;lease.outcome=LeaseNotDispatched;return;
        }
        auto preflight=pool.preflight(session,1);
        if(preflight!=StrongLeaseResult::Ok) {
            lease.error=static_cast<uint32_t>(preflight);lease.outcome=LeaseNotDispatched;
            lease.active=pool.active();return;
        }
        // The pool owns the token before any serial allocation. On uncertain
        // stabilization it retains that holder until ordered session cleanup.
        lease.outcome=LeaseUnknown;
        auto result=pool.acquire(ops,session,lease.object.address,lease.token);
        lease.error=static_cast<uint32_t>(result);
        if(result==StrongLeaseResult::Ok) {
            if(stabilize_retained_identity(ops,lease.object))lease.outcome=LeaseCompleted;
            else lease.error=413;
        }
        lease.active=pool.active();return;
}
