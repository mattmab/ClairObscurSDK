#include "owned_button_delegate.h"
#include "button_delegate_contract.h"
#include <cassert>
#include <cstdio>
#include <stdexcept>

struct Ops {
    bool thread=true, valid=true, fail_after_write=false, freed=false;
    uint64_t table=100;
    unsigned writes=0;
    bool on_thread() const { return thread; }
    bool validate(uint64_t instance,uint64_t original,uint64_t shadow) const {
        return valid && instance==1 && original==100 && shadow==200 && !freed;
    }
    uint64_t exchange(uint64_t instance,uint64_t next,uint64_t expected) {
        assert(instance==1 && !freed);
        ++writes;
        auto previous=table;
        if(table==expected) table=next;
        if(fail_after_write) throw std::runtime_error("unknown exchange outcome");
        return previous;
    }
};

static void* destroy_stub(void* self,uint32_t) { return self; }
static void* execute_stub(void*,void* reply) { return reply; }
static bool safe_stub(void*) { return true; }

int main() {
    namespace Contract=ButtonDelegateContract;
    Contract::Table observed{}, shadow{};
    constexpr uint64_t base=0x140000000;
    for(size_t i=0;i<Contract::slot_count;++i) observed[i]=base+Contract::entries[i];
    assert(Contract::prepare(base,observed,shadow,destroy_stub,execute_stub,safe_stub));
    for(size_t i=0;i<Contract::slot_count;++i)
        if(i!=Contract::destroy_slot && i!=Contract::execute_slot && i!=Contract::safe_slot)
            assert(shadow[i]==observed[i]);
    auto unchanged=shadow;
    observed[8]+=1; // Reject a changed clone entry before publishing anything.
    assert(!Contract::prepare(base,observed,shadow,destroy_stub,execute_stub,safe_stub));
    assert(shadow==unchanged);
    using Result=ButtonDelegateResult;
    MenuActionEvents<> queue;
    assert(queue.open(7));
    OwnedButtonDelegate binding(queue);
    Ops ops;
    auto install=[&] { return binding.install(ops,7,9,11,1,100,200); };
    MenuActionEvent event{};
    ops.thread=false;
    assert(install()==Result::Invalid && !binding.protects_owner());
    ops.thread=true; ops.valid=false;
    assert(install()==Result::Invalid && ops.writes==0);
    ops.valid=true;
    assert(install()==Result::Ok && ops.table==200 && binding.protects_owner());
    assert(install()==Result::Busy);
    auto click=binding.enter(1);
    assert(click.registration && !binding.enter(2).registration);
    binding.leave(click,true);
    assert(queue.pop(7,event) && event.ticket.action==11);
    binding.leave(binding.enter(1),false);
    assert(!queue.pop(7,event));

    // A synchronous close inside the original revokes immediately but keeps
    // ownership until that call has unwound. No stale completion is delivered.
    auto nested=binding.enter(1);
    assert(binding.close(ops)==Result::Deferred && ops.table==200);
    assert(!binding.enter(1).registration);
    binding.leave(nested,true);
    assert(!queue.pop(7,event));
    assert(binding.close(ops)==Result::Ok && ops.table==100 && !binding.protects_owner());

    assert(install()==Result::Ok);
    auto destruction=binding.enter(1);
    assert(binding.destroying(ops,1) && ops.table==100);
    ops.freed=true;
    assert(!binding.destroying(ops,1));
    assert(binding.close(ops)==Result::Deferred);
    binding.leave(destruction,true);
    auto writes=ops.writes;
    assert(binding.close(ops)==Result::Ok && ops.writes==writes);
    assert(!queue.pop(7,event)); // No dereference after destructor/free.

    ops.freed=false;
    assert(install()==Result::Ok);
    binding.leave(binding.enter(1),true);
    ops.table=300; // Never overwrite a different owner's replacement.
    assert(binding.close(ops)==Result::Quarantined && ops.table==300);
    assert(binding.protects_owner() && !queue.pop(7,event));
    writes=ops.writes;
    assert(binding.close(ops)==Result::Quarantined && ops.writes==writes);

    MenuActionEvents<> other_queue;
    assert(other_queue.open(8));
    OwnedButtonDelegate interrupted(other_queue);
    Ops interrupted_ops; interrupted_ops.fail_after_write=true;
    try { interrupted.install(interrupted_ops,8,1,2,1,100,200); assert(false); }
    catch(const std::runtime_error&) { interrupted.quarantine(); }
    assert(interrupted_ops.table==200 && interrupted.protects_owner());
    writes=interrupted_ops.writes;
    assert(interrupted.close(interrupted_ops)==Result::Quarantined && interrupted_ops.writes==writes);
    assert(!other_queue.begin(1).registration);

    MenuActionEvents<> restore_queue;
    assert(restore_queue.open(9));
    OwnedButtonDelegate restore_interrupted(restore_queue);
    Ops restore_ops;
    assert(restore_interrupted.install(restore_ops,9,1,2,1,100,200)==Result::Ok);
    restore_ops.fail_after_write=true;
    try { restore_interrupted.close(restore_ops); assert(false); }
    catch(const std::runtime_error&) { restore_interrupted.quarantine(); }
    assert(restore_ops.table==100 && restore_interrupted.protects_owner());
    writes=restore_ops.writes;
    assert(restore_interrupted.close(restore_ops)==Result::Quarantined && restore_ops.writes==writes);
    std::puts("Delegate lifecycle: reentrant revoke, destruction, conflict and unknown-outcome tests passed.");
}
