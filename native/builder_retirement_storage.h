#pragma once
#include <cstdint>
namespace e33_builder {
// Called only after the owning epoch's independent retirement proof. Keep an
// unacknowledged token unchanged; never infer cleanup from a missing UObject.
template<class Pool,class Ops>
uint32_t release_retired_storage(Pool&pool,Ops&ops,uint64_t session,uint64_t address,uint64_t&token){
    if(!token)return 0;
    if(!pool.owns_retirement_storage(session,token,address))return 1968;
    const auto result=pool.release(ops,session,token);
    if(result==StrongLeaseResult::Deferred)return 407;
    if(result!=StrongLeaseResult::Ok)return 1968;
    token=0;return 0;
}
}
