#include "button_delegate_pool.h"
#include <cassert>
#include <cstdio>

struct Ops {
    static inline bool thread=true;
    static inline bool fault=false;
    uint64_t instance;
    uint64_t& table;
    bool on_thread() const { return thread; }
    bool faulted() const { return fault; }
    bool validate(uint64_t id,uint64_t original,uint64_t shadow) const {
        return id==instance && table==original && original==100 && shadow==200;
    }
    uint64_t exchange(uint64_t id,uint64_t next,uint64_t expected) {
        assert(id==instance);
        auto old=table; if(old==expected) table=next; return old;
    }
};
int main() {
    using Result=ButtonDelegateResult;
    ButtonDelegatePool<2> pool;
    uint64_t tables[4]={100,100,100,100};
    auto ops=[&](uint64_t id) { assert(id>=1 && id<=4); return Ops{id,tables[id-1]}; };
    auto a=ops(1),b=ops(2),c=ops(3);
    assert(pool.open(7));
    assert(pool.install(a,7,10,11,1,100,200)==Result::Ok);
    assert(pool.install(b,7,10,12,2,100,200)==Result::Ok);
    assert(pool.install(c,7,10,13,3,100,200)==Result::Busy && tables[2]==100);
    assert(pool.install(a,7,10,14,1,100,200)==Result::Busy);
    auto* first=pool.find(1); auto* second=pool.find(2);
    auto old=first->enter(1); first->leave(old,true);
    second->leave(second->enter(2),true);
    Ops::thread=false;
    assert(pool.close(ops)==Result::Deferred && tables[0]==200 && tables[1]==200);
    Ops::thread=true;
    assert(pool.remove(a,7,1)==Result::Ok && !pool.find(1));
    MenuActionEvent event{};
    assert(pool.pop(7,event) && event.ticket.action==12); // Only removed control's event purged.
    assert(!pool.pop(7,event));
    assert(pool.install(c,7,10,13,3,100,200)==Result::Ok);
    assert(pool.find(3)==first); // Stable slot is reusable only after acknowledged close.
    first->leave(old,true); assert(!pool.pop(7,event));
    auto active=second->enter(2);
    first->leave(first->enter(3),true);
    assert(pool.close(ops)==Result::Deferred);
    assert(!pool.pop(7,event) && pool.protects_owner());
    assert(!pool.open(8));
    assert(pool.install(a,7,10,15,1,100,200)==Result::Invalid);
    second->leave(active,true); assert(!pool.pop(7,event));
    assert(pool.close(ops)==Result::Ok && !pool.protects_owner());
    assert(tables[0]==100 && tables[1]==100 && tables[2]==100);
    assert(pool.open(8));
    assert(pool.install(a,8,10,11,1,100,200)==Result::Ok);
    auto fresh=pool.find(1)->enter(1);
    assert(fresh.registration>old.registration);
    pool.find(1)->leave(fresh,true);
    pool.quarantine(); assert(!pool.pop(8,event));
    assert(pool.close(ops)==Result::Quarantined && pool.protects_owner());
    assert(!pool.open(9));

    ButtonDelegatePool<2> destruction;
    tables[0]=tables[1]=100;
    assert(destruction.open(20));
    assert(destruction.install(a,20,30,40,1,100,200)==Result::Ok);
    assert(destruction.install(b,20,30,41,2,100,200)==Result::Ok);
    auto* destroyed=destruction.find(1);
    assert(destroyed->destroying(a,1));
    tables[0]=999; // A destroyed instance must not be exchanged during cleanup.
    assert(destruction.remove(a,20,1)==Result::Ok && tables[0]==999);
    Ops::fault=true;
    assert(destruction.close(ops)==Result::Quarantined);
    assert(tables[1]==200 && destruction.protects_owner());
    Ops::fault=false;
    assert(destruction.close(ops)==Result::Quarantined);
    std::puts("Multi-control routing, revocation, stable reuse, deferred close and quarantine passed.");
}
