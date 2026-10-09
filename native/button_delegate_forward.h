#pragma once
#include <Windows.h>
#include "owned_button_delegate.h"
#include "button_delegate_contract.h"

// Forwarding candidate. Original entries must be immutable and non-null before
// publishing any thunk; thunk/table storage must remain pinned until process exit.
// Ops::foreign_call() must atomically latch a permanent fault without touching
// the game-thread queue. Every owner-thread control/drain operation must inspect
// that latch and quarantine before touching a possibly freed delegate.
template<class Binding,class Ops>
struct ButtonDelegateForward {
    static MenuActionTicket begin(Binding& binding,Ops& ops,void* instance) {
        if(!ops.on_thread()) { ops.foreign_call(); return {}; }
        if(ops.faulted()) { binding.quarantine(); return {}; }
        return binding.enter(reinterpret_cast<uint64_t>(instance));
    }
    static void* execute(Binding& binding,Ops& ops,ButtonDelegateContract::Execute original,
                         void* instance,void* reply) {
        const auto ticket=begin(binding,ops,instance);
        void* result=nullptr;
        bool returned=false;
        __try {
            result=original(instance,reply);
            returned=true;
        } __finally {
            if(ticket.registration) {
                binding.leave(ticket,returned);
                if(!returned) binding.quarantine();
            }
        }
        // Preserve exactly the original return pointer and reply bytes.
        return result;
    }
    static bool execute_if_safe(Binding& binding,Ops& ops,ButtonDelegateContract::ExecuteIfSafe original,
                                void* instance) {
        const auto ticket=begin(binding,ops,instance);
        bool result=false, returned=false;
        __try {
            result=original(instance);
            returned=true;
        } __finally {
            if(ticket.registration) {
                binding.leave(ticket,returned && result);
                if(!returned) binding.quarantine();
            }
        }
        return result;
    }
    static void* destroy(Binding& binding,Ops& ops,ButtonDelegateContract::Destroy original,
                         void* instance,uint32_t flags) {
        if(!ops.on_thread()) ops.foreign_call();
        else {
            __try {
                if(ops.faulted()) binding.quarantine();
                else binding.destroying(ops,reinterpret_cast<uint64_t>(instance));
            } __except(EXCEPTION_EXECUTE_HANDLER) {
                // Contain only SDK pre-destruction bookkeeping faults. The
                // original destructor still runs exactly once, outside this
                // handler; its exceptions retain the engine's normal semantics.
                binding.quarantine();
            }
        }
        return original(instance,flags);
    }
};
