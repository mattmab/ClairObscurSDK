#include "strong_lease_pool.h"
#include <cassert>
#include <set>
#include <thread>
#include <vector>
#include <cstdio>
struct GrowthOps {
    std::set<TargetStrongReference*> allocations;
    bool releasable=true;
    bool can_create(uint64_t object) const { return object==100; }
    bool can_release() const { return releasable; }
    uint64_t base_vtable() const { return 1; }
    uint64_t strong_vtable() const { return 2; }
    bool barrier_needed() const { return false; }
    void write_barrier(uint64_t) {}
    TargetStrongReference* allocate() { auto* p=new TargetStrongReference{};allocations.insert(p);return p; }
    void register_holder(TargetStrongReference* p) { p->registered=1; }
    void destroy(TargetStrongReference* p) { assert(allocations.erase(p)==1);delete p; }
};
int main() {
    LeaseBlocks<uint64_t,4,256> storage;
    auto* stable=&storage.at(0);*stable=123;
    for(size_t needed=5;needed<=256;++needed) {
        assert(storage.reserve(needed));assert(&storage.at(0)==stable && *stable==123);
    }
    assert(!storage.reserve(257));
    using R=StrongLeaseResult;
    GrowthOps ops;StrongLeasePool<4,256> pool;
    assert(pool.begin(1)==R::Ok);assert(pool.configure(200,70,20));
    const auto before_bytes=pool.storage_bytes();
    std::vector<uint64_t> tokens;
    for(uint64_t owner=1;owner<=3;++owner) {
        assert(pool.set_owner(1,owner));
        const unsigned count=owner==3 ? 40 : 70;
        for(unsigned i=0;i<count;++i) {
            uint64_t token{};assert(pool.acquire(ops,1,100,token)==R::Ok);tokens.push_back(token);
            for(auto old:tokens) assert(pool.owns_object(1,old,100));
        }
        uint64_t rejected{};assert(pool.acquire(ops,1,100,rejected)==R::Capacity && !rejected);
    }
    assert(pool.active()==180 && pool.peak()==180 && pool.capacity()>=180);
    // Normal owners cannot spend the remaining critical budget.
    assert(pool.set_owner(1,4));assert(pool.preflight(1,1)==R::Capacity);
    assert(pool.preflight(1,0)==R::Ok);
    assert(pool.set_owner(1,0));
    for(unsigned i=0;i<20;++i) { uint64_t token{};assert(pool.acquire(ops,1,100,token)==R::Ok);tokens.push_back(token); }
    uint64_t rejected{};assert(pool.acquire(ops,1,100,rejected)==R::Capacity);
    assert(pool.active()==200 && pool.peak()==200);
    // Wrong-thread requests fail before touching pool/engine storage.
    std::vector<std::thread> workers;
    for(unsigned i=0;i<8;++i) workers.emplace_back([&] {
        uint64_t token{};
        assert(pool.acquire(ops,1,100,token)==R::InvalidContext);
        assert(pool.release(ops,1,tokens[0])==R::InvalidContext);
        assert(pool.close(ops,1)==R::InvalidContext);
    });
    for(auto& worker:workers) worker.join();
    assert(pool.active()==200);
    const auto old=tokens.back();assert(pool.release(ops,1,old)==R::Ok);
    assert(pool.release(ops,1,old)==R::Stale);
    uint64_t replacement{};assert(pool.acquire(ops,1,100,replacement)==R::Ok && replacement>old);
    unsigned owners=0;
    pool.owner_statistics([&](uint64_t owner,uint32_t active,uint32_t peak) {
        ++owners;assert(active==peak);if(owner==0) assert(active==20);
    });
    assert(owners==4);
    ops.releasable=false;assert(pool.close(ops,1)==R::Deferred);
    assert(pool.acquire(ops,1,100,rejected)==R::Busy);
    ops.releasable=true;assert(pool.close(ops,1)==R::Ok && ops.allocations.empty());
    assert(pool.begin(2)==R::Ok && pool.peak()==0);
    assert(pool.release(ops,2,old)==R::Stale);
    assert(pool.release(ops,1,replacement)==R::SessionMismatch);
    assert(pool.acquire(ops,2,100,replacement)==R::Ok && replacement>old);
    assert(pool.close(ops,2)==R::Ok && ops.allocations.empty());
    std::printf("Growth/reuse/thread/quota/reserve/cleanup passed; storage before=%zu after=%zu bytes; peak holders=200 (4800 holder bytes, allocator overhead excluded)\n",before_bytes,pool.storage_bytes());
}
