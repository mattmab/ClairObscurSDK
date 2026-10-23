#include <cstdint>
#include <cassert>
enum class StrongLeaseResult {Ok,Deferred,Quarantined};
#include "builder_retirement_storage.h"
struct Ops{};
struct Pool{
 bool owns=true;unsigned checks=0,releases=0;StrongLeaseResult result=StrongLeaseResult::Ok;
 bool owns_retirement_storage(uint64_t session,uint64_t token,uint64_t address){
  ++checks;assert(session==5&&token==7&&address==0x10000);return owns;
 }
 StrongLeaseResult release(Ops&,uint64_t session,uint64_t token){++releases;assert(session==5&&token==7);return result;}
};
int main(){
 Ops ops;Pool pool;uint64_t token=7;
 pool.owns=false;assert(e33_builder::release_retired_storage(pool,ops,5,0x10000,token)==1968);
 assert(token==7&&!pool.releases);
 pool.owns=true;pool.result=StrongLeaseResult::Deferred;
 assert(e33_builder::release_retired_storage(pool,ops,5,0x10000,token)==407&&token==7);
 pool.result=StrongLeaseResult::Quarantined;
 assert(e33_builder::release_retired_storage(pool,ops,5,0x10000,token)==1968&&token==7);
 pool.result=StrongLeaseResult::Ok;
 assert(!e33_builder::release_retired_storage(pool,ops,5,0x10000,token)&&!token);
 const auto released=pool.releases,checked=pool.checks;
 assert(!e33_builder::release_retired_storage(pool,ops,5,0x10000,token));
 assert(pool.releases==released&&pool.checks==checked);
}
