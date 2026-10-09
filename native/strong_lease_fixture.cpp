#include "strong_lease_pool.h"
#include <cstdio>
#include <stdexcept>
#include <set>

static void check(bool value,const char* message) {
    if(!value) throw std::runtime_error(message);
}
struct Engine {
    std::set<TargetStrongReference*> allocations;
    bool allowed=true, releasable=true, reject=false, fault=false;
    unsigned registrations=0, frees=0;
    ~Engine() { for(auto* p:allocations) delete p; }
    uint64_t base_vtable() const { return 1; }
    uint64_t strong_vtable() const { return 2; }
    bool can_create(uint64_t object) const { return allowed && object==100; }
    bool can_release() const { return releasable; }
    TargetStrongReference* allocate() {
        auto* result=new TargetStrongReference{}; allocations.insert(result); return result;
    }
    void register_holder(TargetStrongReference* p) {
        ++registrations;
        if(fault) throw std::runtime_error("registration interrupted");
        p->registered=!reject;
    }
    bool barrier_needed() const { return false; }
    void write_barrier(uint64_t) {}
    void destroy(TargetStrongReference* p) {
        check(allocations.erase(p)==1,"destroy must own allocation");
        ++frees; delete p;
    }
};
int main() {
    using R=StrongLeaseResult;
    Engine engine; StrongLeasePool<2> pool;
    uint64_t a=99,b=99,c=99;
    check(pool.begin(0)==R::SessionMismatch,"reject empty session");
    check(pool.begin(10)==R::Ok,"begin");
    check(pool.preflight(11,1)==R::SessionMismatch,"preflight session ownership");
    check(pool.preflight(10,2)==R::Ok && !pool.active(),"preflight has no side effects");
    check(pool.acquire(engine,11,100,a)==R::SessionMismatch && a==0,"wrong session");
    check(pool.acquire(engine,10,100,a)==R::Ok && a,"first lease");
    check(pool.owns_object(10,a,100),"owned assignment target");
    check(!pool.owns_object(11,a,100) && !pool.owns_object(10,a,101) && !pool.owns_object(10,0,100),"assignment lease binding");
    check(pool.acquire(engine,10,100,b)==R::Ok && b!=a,"independent ownership for same object");
    check(pool.active()==2 && engine.allocations.size()==2,"two native holders");
    check(pool.preflight(10,1)==R::Capacity,"preflight rejects before dispatch");
    check(pool.preflight(10,0)==R::Ok,"scalar calls require no holder slots");
    check(pool.acquire(engine,10,100,c)==R::Capacity && !c,"bounded capacity");
    check(pool.release(engine,11,a)==R::SessionMismatch,"cross-session release rejected");
    check(pool.release(engine,10,a)==R::Ok && pool.active()==1,"release exactly one");
    check(!pool.owns_object(10,a,100),"released token cannot authorize assignment");
    check(pool.release(engine,10,a)==R::Stale,"stale token rejected");
    check(pool.acquire(engine,10,100,c)==R::Ok && c!=a && c!=b,"slot reuse changes token");
    engine.releasable=false;
    check(pool.close(engine,10)==R::Deferred && pool.active()==2,"deferred close keeps ownership");
    check(pool.begin(20)==R::Busy,"cannot reopen before cleanup");
    engine.releasable=true;
    check(pool.close(engine,10)==R::Ok && !pool.active() && engine.allocations.empty(),"close releases all");
    check(pool.begin(20)==R::Ok,"new session after cleanup");
    check(pool.release(engine,20,c)==R::Stale,"prior-session token stale");
    check(pool.acquire(engine,20,100,b)==R::Ok && b>c,"token monotonic across sessions");
    check(pool.close(engine,20)==R::Ok,"second close");
    check(pool.begin(30)==R::Ok,"rejection session");
    engine.reject=true;
    check(pool.acquire(engine,30,100,a)==R::RegistrationRejected && !a && !pool.active(),"rejection rolls back slot");
    check(engine.allocations.empty(),"rejection frees unregistered holder");
    check(pool.close(engine,30)==R::Ok,"empty close");
    check(pool.begin(40)==R::Ok,"fault session");
    engine.reject=false; engine.fault=true;
    try { pool.acquire(engine,40,100,a); } catch(const std::runtime_error&) {}
    check(!a && pool.active()==1 && engine.allocations.size()==1,"fault remains tracked without returning token");
    auto* holder=*engine.allocations.begin();
    check(holder->vtable==engine.strong_vtable() && holder->object==100,"fault leaves complete engine collector");
    check(pool.close(engine,40)==R::Quarantined && pool.active()==1,"quarantine not silently discarded");
    check(pool.begin(50)==R::Busy,"quarantine prevents session reuse");
    std::puts("Strong lease pool: capacity, stale tokens, session isolation, deferred close and quarantine passed.");
}
