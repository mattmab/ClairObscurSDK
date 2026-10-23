#include "stable_lease_runtime.h"
#include <cassert>
#include <map>
#include <set>
struct Engine{
 std::map<int,CallIdentity> ids;std::set<TargetStrongReference*> holders;
 CallIdentity expected{1,0,0x10000};bool allowed=true,releasable=true,replace=false;unsigned allocations=0,serials=0,frees=0;
 ~Engine(){for(auto*p:holders)delete p;}
 uint64_t base_vtable()const{return 1;}uint64_t strong_vtable()const{return 2;}
 bool can_create(uint64_t object)const{auto id=capture(object);return allowed&&id.index==expected.index&&id.serial==expected.serial&&id.address==expected.address;}
 bool can_release()const{return releasable;}bool can_assign()const{return allowed;}
 CallIdentity capture(uint64_t address)const{for(const auto& item:ids)if(item.second.address==address)return item.second;return {-1,0,0};}
 int32_t allocate_serial(int index){++serials;auto& id=ids.at(index);id.serial=1001+index;if(replace)id.address+=8;return id.serial;}
 TargetStrongReference*allocate(){++allocations;auto*p=new TargetStrongReference{};holders.insert(p);return p;}
 void register_holder(TargetStrongReference*p){p->registered=1;}bool barrier_needed()const{return false;}void write_barrier(uint64_t){}
 void destroy(TargetStrongReference*p){assert(holders.erase(p)==1);delete p;++frees;}
};

struct UncertainPool {
    bool acquired=false;
    StrongLeaseResult preflight(uint64_t,uint32_t){return StrongLeaseResult::Ok;}
    StrongLeaseResult acquire(Engine&,uint64_t,uint64_t,uint64_t&token){acquired=true;token=0;return StrongLeaseResult::Quarantined;}
    uint32_t active()const{return acquired?1:0;}
};
static LeasePacket make(Engine&e){LeasePacket p{};p.object={1,0,0x10000};e.ids[1]=p.object;return p;}
int main(){
 {Engine e;StrongLeasePool<128>pool;pool.begin(7);auto p=make(e);stable_lease_acquire(p,e,pool,7);
  assert(!p.error&&p.outcome==LeaseCompleted&&p.token&&p.object.serial==1002&&pool.owns_object(7,p.token,p.object.address));
  e.releasable=false;assert(pool.release(e,7,p.token)==StrongLeaseResult::Deferred);
  e.releasable=true;assert(pool.release(e,7,p.token)==StrongLeaseResult::Ok&&pool.active()==0&&e.frees==1);
 }
 {Engine e;StrongLeasePool<128>pool;pool.begin(7);auto p=make(e);e.ids[1].serial=1009;
  stable_lease_acquire(p,e,pool,7);assert(p.error==402&&p.outcome==LeaseNotDispatched&&!e.allocations&&!e.serials);
 }
 {Engine e;StrongLeasePool<128>pool;pool.begin(7);auto p=make(e);e.allowed=false;
  stable_lease_acquire(p,e,pool,7);assert(p.outcome==LeaseNotDispatched&&!e.allocations&&!e.serials);
 }
 {Engine e;StrongLeasePool<128>pool;pool.begin(7);auto p=make(e);e.replace=true;
  stable_lease_acquire(p,e,pool,7);assert(p.error==413&&p.outcome==LeaseUnknown&&p.token&&pool.active()==1);
  assert(pool.close(e,7)==StrongLeaseResult::Ok&&e.frees==1);
 }
 {Engine e;UncertainPool pool;auto p=make(e);stable_lease_acquire(p,e,pool,7);
  assert(p.error==408&&p.outcome==LeaseUnknown&&!p.token&&pool.active()==1&&!e.serials);
 }
 {Engine e;StrongLeasePool<128>pool;pool.begin(7);auto p=make(e);
  for(unsigned i=0;i<128;++i){uint64_t t=0;assert(pool.acquire(e,7,p.object.address,t)==StrongLeaseResult::Ok);}
  auto allocations=e.allocations;stable_lease_acquire(p,e,pool,7);
  assert(p.error==401&&p.outcome==LeaseNotDispatched&&!p.token&&!e.serials&&e.allocations==allocations);
  assert(pool.close(e,7)==StrongLeaseResult::Ok);
 }
}
