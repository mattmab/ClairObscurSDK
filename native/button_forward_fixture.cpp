#include "button_delegate_forward.h"
#include <cassert>
#include <cstdio>
#include <cstring>

using TestQueue=MenuActionEvents<>;
using TestBinding=OwnedButtonDelegate<TestQueue>;
static constexpr DWORD fault_code=0xe0423341;
struct TestOps {
    DWORD thread=GetCurrentThreadId();
    volatile LONG fault=0;
    uint64_t table=100;
    bool fail_exchange=false, freed=false;
    bool on_thread() const { return GetCurrentThreadId()==thread; }
    void foreign_call() { InterlockedExchange(&fault,1); }
    bool faulted() { return InterlockedCompareExchange(&fault,0,0)!=0; }
    bool validate(uint64_t instance,uint64_t original,uint64_t shadow) const {
        return instance==1 && original==100 && shadow==200 && !freed;
    }
    uint64_t exchange(uint64_t instance,uint64_t next,uint64_t expected) {
        assert(instance==1 && !freed);
        auto previous=table;
        if(table==expected) table=next;
        if(fail_exchange) RaiseException(fault_code,0,0,nullptr);
        return previous;
    }
};
using Forward=ButtonDelegateForward<TestBinding,TestOps>;
static TestQueue test_queue;
static TestBinding test_binding(test_queue);
static TestOps test_ops;
static unsigned calls=0;
static bool throw_original=false, safe_result=true, close_inside=false;
static uint32_t observed_flags=0;
static unsigned char reply_pattern[192];
static void* original_execute(void* instance,void* reply) {
    assert(instance==reinterpret_cast<void*>(1));
    ++calls;
    if(throw_original) RaiseException(fault_code,0,0,nullptr);
    std::memcpy(reply,reply_pattern,sizeof(reply_pattern));
    if(close_inside) assert(test_binding.close(test_ops)==ButtonDelegateResult::Deferred);
    return reply;
}
static bool original_safe(void* instance) {
    assert(instance==reinterpret_cast<void*>(1));
    ++calls;
    if(throw_original) RaiseException(fault_code,0,0,nullptr);
    return safe_result;
}
static void* original_destroy(void* instance,uint32_t flags) {
    ++calls; observed_flags=flags; test_ops.freed=true;
    if(throw_original) RaiseException(fault_code,0,0,nullptr);
    return instance;
}
static bool catch_execute_fault() {
    unsigned char reply[192]{};
    __try { Forward::execute(test_binding,test_ops,original_execute,reinterpret_cast<void*>(1),reply); }
    __except(GetExceptionCode()==fault_code ? EXCEPTION_EXECUTE_HANDLER : EXCEPTION_CONTINUE_SEARCH) { return true; }
    return false;
}
static bool catch_safe_fault(TestBinding& value,TestOps& operations) {
    __try { Forward::execute_if_safe(value,operations,original_safe,reinterpret_cast<void*>(1)); }
    __except(GetExceptionCode()==fault_code ? EXCEPTION_EXECUTE_HANDLER : EXCEPTION_CONTINUE_SEARCH) { return true; }
    return false;
}
static bool catch_destroy_fault(TestBinding& value,TestOps& operations) {
    __try { Forward::destroy(value,operations,original_destroy,reinterpret_cast<void*>(1),1); }
    __except(GetExceptionCode()==fault_code ? EXCEPTION_EXECUTE_HANDLER : EXCEPTION_CONTINUE_SEARCH) { return true; }
    return false;
}
static DWORD WINAPI foreign_execute(void*) {
    unsigned char reply[192]{};
    Forward::execute(test_binding,test_ops,original_execute,reinterpret_cast<void*>(1),reply);
    return 0;
}
int main() {
    assert(test_queue.open(7));
    assert(test_binding.install(test_ops,7,8,9,1,100,200)==ButtonDelegateResult::Ok);
    for(size_t i=0;i<sizeof(reply_pattern);++i) reply_pattern[i]=static_cast<unsigned char>(i^0xa5);
    unsigned char reply[192]{};
    MenuActionEvent event{};
    assert(Forward::execute(test_binding,test_ops,original_execute,reinterpret_cast<void*>(1),reply)==reply);
    assert(calls==1 && std::memcmp(reply,reply_pattern,sizeof(reply))==0);
    assert(test_queue.pop(7,event) && event.ticket.action==9 && !test_queue.pop(7,event));
    safe_result=false;
    assert(!Forward::execute_if_safe(test_binding,test_ops,original_safe,reinterpret_cast<void*>(1)));
    assert(!test_queue.pop(7,event));
    safe_result=true;
    assert(Forward::execute_if_safe(test_binding,test_ops,original_safe,reinterpret_cast<void*>(1)));
    assert(test_queue.pop(7,event) && !test_queue.pop(7,event));
    close_inside=true;
    Forward::execute(test_binding,test_ops,original_execute,reinterpret_cast<void*>(1),reply);
    assert(!test_queue.pop(7,event));
    assert(test_binding.close(test_ops)==ButtonDelegateResult::Ok);
    close_inside=false;
    Forward::execute(test_binding,test_ops,original_execute,reinterpret_cast<void*>(1),reply);
    assert(!test_queue.pop(7,event)); // Late fetched thunk after close is passthrough.
    assert(test_binding.install(test_ops,7,8,9,1,100,200)==ButtonDelegateResult::Ok);
    auto before=calls;
    assert(Forward::destroy(test_binding,test_ops,original_destroy,reinterpret_cast<void*>(1),0)==reinterpret_cast<void*>(1));
    assert(calls==before+1 && observed_flags==0 && test_ops.table==100);
    assert(test_binding.close(test_ops)==ButtonDelegateResult::Ok); // No access after free.
    test_ops.freed=false;
    assert(test_binding.install(test_ops,7,8,9,1,100,200)==ButtonDelegateResult::Ok);
    throw_original=true;
    before=calls;
    assert(catch_execute_fault() && calls==before+1);
    assert(test_binding.state()==ButtonDelegateState::Quarantined && !test_queue.pop(7,event));
    // The module must keep forwarding even after revocation/quarantine.
    throw_original=false;
    before=calls;
    HANDLE worker=CreateThread(nullptr,0,foreign_execute,nullptr,0,nullptr);
    assert(worker && WaitForSingleObject(worker,5000)==WAIT_OBJECT_0);
    CloseHandle(worker);
    assert(calls==before+1 && test_ops.faulted() && !test_queue.pop(7,event));
    test_ops.fail_exchange=true;
    before=calls;
    assert(Forward::destroy(test_binding,test_ops,original_destroy,reinterpret_cast<void*>(1),1)==reinterpret_cast<void*>(1));
    assert(calls==before+1 && observed_flags==1);

    TestQueue cleanup_queue;
    TestBinding cleanup_binding(cleanup_queue);
    TestOps cleanup_ops;
    assert(cleanup_queue.open(8));
    assert(cleanup_binding.install(cleanup_ops,8,1,2,1,100,200)==ButtonDelegateResult::Ok);
    cleanup_ops.fail_exchange=true;
    before=calls;
    assert(Forward::destroy(cleanup_binding,cleanup_ops,original_destroy,reinterpret_cast<void*>(1),0)==reinterpret_cast<void*>(1));
    assert(calls==before+1 && observed_flags==0 && cleanup_ops.table==100);
    assert(cleanup_binding.state()==ButtonDelegateState::Quarantined);
    assert(!cleanup_queue.begin(1).registration);

    TestQueue safe_queue;
    TestBinding safe_binding(safe_queue);
    TestOps safe_ops;
    assert(safe_queue.open(9));
    assert(safe_binding.install(safe_ops,9,1,2,1,100,200)==ButtonDelegateResult::Ok);
    throw_original=true;
    before=calls;
    assert(catch_safe_fault(safe_binding,safe_ops) && calls==before+1);
    assert(safe_binding.state()==ButtonDelegateState::Quarantined && !safe_queue.pop(9,event));
    before=calls;
    assert(catch_destroy_fault(safe_binding,safe_ops) && calls==before+1);
    // Original destructor exception was not swallowed or replayed by the SDK.
    throw_original=false;
    TestQueue fault_queue;
    TestBinding fault_binding(fault_queue);
    TestOps fault_ops;
    assert(fault_queue.open(10));
    assert(fault_binding.install(fault_ops,10,1,2,1,100,200)==ButtonDelegateResult::Ok);
    fault_binding.leave(fault_binding.enter(1),true);
    assert(button_delegate_control_gate(fault_binding,fault_ops)==ButtonDelegateResult::Ok);
    fault_ops.foreign_call();
    fault_ops.freed=true; // A foreign destructor may have already freed storage.
    assert(button_delegate_control_gate(fault_binding,fault_ops)==ButtonDelegateResult::Quarantined);
    assert(!fault_queue.pop(10,event) && !fault_queue.begin(1).registration);
    assert(fault_binding.protects_owner());
    std::puts("Native forwarding: reply bytes, optional success, reentrant close, SEH and foreign-thread passthrough passed.");
}
