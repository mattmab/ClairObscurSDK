#pragma once
#include "lease_release_batch_protocol.h"
namespace e33_lease_batch {
// Exact opaque tokens only. Ops delegates to the SAME native protections and
// StrongLeasePool.release as single releases. Pool journals survive faults.
template<class Ops> void run(Packet& p,Ops& ops){
    if(!valid(p)){p.error=3910;return;}
    // Entire-input preflight: no destructive call on malformed/foreign/protected
    // lists. Each release also rechecks protectors immediately before dispatch.
    for(unsigned i=0;i<p.count;++i){
        const auto error=ops.admit(p.rows[i].token);
        if(error){p.error=error;p.failed=i+1;p.active=ops.active();return;}
    }
    for(unsigned i=0;i<p.count;++i){
        auto& row=p.rows[i];row.outcome=Unknown; // Publish before any destructor.
        const auto error=ops.release(row.token);row.error=error;p.completed=i+1;
        if(!error)row.outcome=Released;
        else if(error==407)row.outcome=Deferred;
        else{
            row.outcome=error==408?Unknown:Rejected;p.error=error;p.failed=i+1;
            p.active=ops.active();return; // Suffix was NOT dispatched.
        }
    }
    p.active=ops.active();
}
}
