#include "metadata_stabilization_runtime.h"
#include "stable_identity.h"
#include "strong_lease_pool.h"
#include <cassert>
#include <map>
#include <set>
using namespace e33_metadata;
struct Engine{
 std::map<int,CallIdentity> ids;std::set<TargetStrongReference*> holders;
 bool allowed=true,releasable=true,replace=false;unsigned allocations=0,serials=0,frees=0;
 ~Engine(){for(auto*p:holders)delete p;}
 uint64_t base_vtable()const{return 1;}uint64_t strong_vtable()const{return 2;}
 bool can_create(uint64_t object)const{return allowed&&capture(object).address==object;}
 bool can_release()const{return releasable;}bool can_assign()const{return allowed;}
 CallIdentity capture(uint64_t address)const{for(const auto& item:ids)if(item.second.address==address)return item.second;return {-1,0,0};}
 int32_t allocate_serial(int index){++serials;auto& id=ids.at(index);id.serial=1001+index;if(replace)id.address+=8;return id.serial;}
 TargetStrongReference*allocate(){++allocations;auto*p=new TargetStrongReference{};holders.insert(p);return p;}
 void register_holder(TargetStrongReference*p){p->registered=1;}bool barrier_needed()const{return false;}void write_barrier(uint64_t){}
 void destroy(TargetStrongReference*p){assert(holders.erase(p)==1);delete p;++frees;}
};
struct Ops{
 Engine&engine;StrongLeasePool<128>&pool;std::set<int> denied;
 uint32_t admit(const CallIdentity&id)const{return !engine.can_assign()||!same(engine.capture(id.address),id)||denied.count(id.index)?3921:0;}
 uint32_t preflight(uint32_t count){return uint32_t(pool.preflight(7,count));}
 uint32_t acquire(const CallIdentity&id,uint64_t&token){return uint32_t(pool.acquire(engine,7,id.address,token));}
 bool stabilize(const CallIdentity&id,CallIdentity&after){after=id;return stabilize_retained_identity(engine,after);}
 uint32_t active()const{return pool.active();}
};
static Packet make(Engine&e,unsigned n){Packet p{};p.version=1;p.count=n;for(unsigned i=0;i<n;++i){auto id=CallIdentity{int32_t(i+1),0,0x10000+uint64_t(i)*16};e.ids[id.index]=id;p.rows[i].before=id;}return p;}
int main(){
 {Engine e;StrongLeasePool<128>pool;assert(pool.begin(7)==StrongLeaseResult::Ok);Ops ops{e,pool,{}};auto p=make(e,128);run(p,ops);
  assert(!p.error&&p.completed==128&&pool.active()==128&&e.serials==128);
  for(unsigned i=0;i<128;++i){auto&r=p.rows[i];assert(r.outcome==RetainedStable&&r.before.serial==0&&r.after.serial>1000&&pool.owns_object(7,r.token,r.after.address));}
  auto&r=p.rows[0];e.releasable=false;assert(pool.release(e,7,r.token)==StrongLeaseResult::Deferred&&pool.owns_object(7,r.token,r.after.address));
  e.releasable=true;assert(pool.release(e,7,r.token)==StrongLeaseResult::Ok&&!pool.contains_token(7,r.token));
  assert(pool.close(e,7)==StrongLeaseResult::Ok&&e.frees==128);
 }
 {Engine e;StrongLeasePool<128>pool;pool.begin(7);Ops ops{e,pool,{2}};auto p=make(e,3);run(p,ops);assert(p.error==3921&&!p.completed&&p.failed==2&&!e.allocations);}
 {Engine e;StrongLeasePool<128>pool;pool.begin(7);Ops ops{e,pool,{}};auto p=make(e,2);p.rows[1].before=p.rows[0].before;run(p,ops);assert(p.error==3920&&!e.allocations);}
 {Engine e;StrongLeasePool<128>pool;pool.begin(7);Ops ops{e,pool,{}};auto p=make(e,2);e.ids[1].serial=2010;run(p,ops);assert(p.error==3921&&!e.allocations);}
 {Engine e;StrongLeasePool<128>pool;pool.begin(7);Ops ops{e,pool,{}};auto p=make(e,2);e.replace=true;run(p,ops);assert(p.error==3922&&p.completed==1&&p.rows[0].outcome==Unknown&&p.rows[0].token&&pool.active()==1&&p.rows[1].outcome==NotDispatched);
  assert(pool.close(e,7)==StrongLeaseResult::Ok&&e.frees==1); // Release holder, never purge by stale zero identity.
 }
 {Engine e;StrongLeasePool<128>pool;pool.begin(7);Ops ops{e,pool,{}};auto p=make(e,1);e.allowed=false;run(p,ops);assert(p.error==3921&&!e.allocations);}
 {Engine e;StrongLeasePool<128>pool;pool.begin(7);Ops ops{e,pool,{}};auto p=make(e,2);
  for(unsigned i=0;i<127;++i){uint64_t token=0;assert(pool.acquire(e,7,p.rows[0].before.address,token)==StrongLeaseResult::Ok);}
  const auto before=e.allocations;run(p,ops);assert(p.error==uint32_t(StrongLeaseResult::Capacity)&&!p.completed&&!e.serials&&e.allocations==before&&pool.active()==127);
  assert(pool.close(e,7)==StrongLeaseResult::Ok);
 }
 return 0;
}
