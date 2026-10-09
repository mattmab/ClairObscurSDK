#pragma once
#include "menu_action_events.h"

enum class ButtonDelegateState { Empty, Installing, Active, Revoked, Restoring, Destroyed, Quarantined };
enum class ButtonDelegateResult { Ok, Invalid, Busy, Deferred, Quarantined };

// Candidate lifecycle core, not a published engine hook. All methods run on the
// verified game thread. Ops validates the complete target delegate/table and
// performs an expected-value vtable exchange. Storage and thunks must be pinned.
// The caller contains SEH and calls quarantine() after an unknown mutation;
// Installing/Restoring can never be replayed. Its SButton lease outlives this core.
template<class Queue>
class OwnedButtonDelegate {
    Queue& queue_;
    ButtonDelegateState state_=ButtonDelegateState::Empty;
    uint64_t instance_=0, original_=0, shadow_=0;
    MenuActionTicket ticket_{};
    uint32_t executing_=0;

    void clear() {
        state_=ButtonDelegateState::Empty;
        instance_=original_=shadow_=0; ticket_={};
    }
public:
    explicit OwnedButtonDelegate(Queue& queue):queue_(queue) {}
    OwnedButtonDelegate(const OwnedButtonDelegate&)=delete;
    OwnedButtonDelegate& operator=(const OwnedButtonDelegate&)=delete;
    ButtonDelegateState state() const { return state_; }
    bool protects_owner() const { return state_!=ButtonDelegateState::Empty; }
    void quarantine() {
        queue_.revoke(ticket_);
        state_=ButtonDelegateState::Quarantined;
    }
    template<class Ops>
    ButtonDelegateResult install(Ops& ops,uint64_t session,uint64_t owner,uint64_t action,
                                 uint64_t instance,uint64_t expected_table,uint64_t shadow) {
        if(state_!=ButtonDelegateState::Empty) return ButtonDelegateResult::Busy;
        if(!ops.on_thread() || !instance || !expected_table || !shadow || expected_table==shadow ||
           !ops.validate(instance,expected_table,shadow)) return ButtonDelegateResult::Invalid;
        auto ticket=queue_.bind(session,owner,action,instance);
        if(!ticket.registration) return ButtonDelegateResult::Invalid;
        instance_=instance; original_=expected_table; shadow_=shadow; ticket_=ticket;
        state_=ButtonDelegateState::Installing;
        if(ops.exchange(instance_,shadow_,original_)!=original_) {
            queue_.revoke(ticket_); clear(); return ButtonDelegateResult::Invalid;
        }
        state_=ButtonDelegateState::Active;
        return ButtonDelegateResult::Ok;
    }
    // Adapter calls before forwarding either execute slot. Do not capture the
    // registration after calling Unreal: callbacks can synchronously replace it.
    MenuActionTicket enter(uint64_t instance) {
        if(state_!=ButtonDelegateState::Active || instance!=instance_ ||
           executing_==(std::numeric_limits<uint32_t>::max)()) return {};
        ++executing_;
        return ticket_;
    }
    // Use a finally boundary so a failed original invocation also drops depth.
    // success=false never delivers an action (including ExecuteIfSafe false).
    void leave(const MenuActionTicket& ticket,bool success) {
        if(!executing_ || !ticket.registration || ticket.registration!=ticket_.registration ||
           ticket.session!=ticket_.session) return;
        if(success && state_==ButtonDelegateState::Active) queue_.finish(ticket);
        --executing_;
    }
    template<class Ops>
    ButtonDelegateResult close(Ops& ops) {
        if(state_==ButtonDelegateState::Empty) return ButtonDelegateResult::Ok;
        if(!ops.on_thread()) return ButtonDelegateResult::Deferred;
        if(state_==ButtonDelegateState::Installing || state_==ButtonDelegateState::Restoring ||
           state_==ButtonDelegateState::Quarantined) {
            quarantine(); return ButtonDelegateResult::Quarantined;
        }
        queue_.revoke(ticket_); // Revoke delivery before waiting for expected_table calls.
        if(state_!=ButtonDelegateState::Destroyed) state_=ButtonDelegateState::Revoked;
        if(executing_) return ButtonDelegateResult::Deferred;
        if(state_==ButtonDelegateState::Destroyed) { clear(); return ButtonDelegateResult::Ok; }
        state_=ButtonDelegateState::Restoring;
        auto previous=ops.exchange(instance_,original_,shadow_);
        if(previous!=shadow_ && previous!=original_) {
            quarantine(); return ButtonDelegateResult::Quarantined;
        }
        clear();
        return ButtonDelegateResult::Ok;
    }
    // Invoke before the immutable engine destructor, even for flags=0: that
    // call can be followed by container reuse/free. Never touch the instance
    // after forwarding. A captured execute may still be unwinding afterward.
    template<class Ops>
    bool destroying(Ops& ops,uint64_t instance) {
        if(!ops.on_thread() || !instance || instance!=instance_ ||
           state_==ButtonDelegateState::Empty || state_==ButtonDelegateState::Destroyed) return false;
        queue_.revoke(ticket_);
        // Publish no-further-dereference state before the exchange. Unknown
        // exchange outcomes are still quarantined by the outer SEH boundary.
        state_=ButtonDelegateState::Destroyed;
        ops.exchange(instance_,original_,shadow_); // Preserve a foreign table.
        return true;
    }
};

// Mandatory gate for ALL runtime control and queue-drain entrypoints. Checking
// the permanent foreign-thread latch precedes every delegate dereference. The
// caller still owns SEH containment and may not release leases on quarantine.
template<class Binding,class Ops>
ButtonDelegateResult button_delegate_control_gate(Binding& binding,Ops& ops) {
    if(!ops.on_thread()) return ButtonDelegateResult::Deferred;
    if(ops.faulted()) { binding.quarantine(); return ButtonDelegateResult::Quarantined; }
    if(binding.state()==ButtonDelegateState::Quarantined) return ButtonDelegateResult::Quarantined;
    return ButtonDelegateResult::Ok;
}
