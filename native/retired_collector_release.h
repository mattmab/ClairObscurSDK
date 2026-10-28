#pragma once
#include "strong_lease_pool.h"
// A successful earlier cleanup may already have closed an empty private pool.
// Do not turn remaining reference retirement into a SessionMismatch, and never
// release nonempty storage belonging to another session.
template<class Pool,class Ops> StrongLeaseResult release_retired_collectors(Pool& pool,Ops& ops,uint64_t session) {
    if(!pool.owns(session))return pool.active() ? StrongLeaseResult::Quarantined : StrongLeaseResult::Ok;
    return pool.close(ops,session);
}
