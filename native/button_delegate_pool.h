#pragma once
#include "owned_button_delegate.h"
#include <array>
#include <optional>

// Candidate multi-control owner. All access, including lookup, is game-thread
// only after the adapter's permanent foreign-thread fault gate. The containing
// adapter and every retained Slate reference must remain at stable addresses.
// SEH after an unknown mutation must quarantine the entire pool externally.
template<size_t Controls=16,size_t Events=64>
class ButtonDelegatePool {
public:
    using Queue=MenuActionEvents<Controls,Events>;
    using Binding=OwnedButtonDelegate<Queue>;
private:
    struct Slot { uint64_t instance=0; std::optional<Binding> binding; };
    Queue queue_;
    std::array<Slot,Controls> slots_{};
    uint64_t session_=0;
    bool closing_=false;
    Slot* slot(uint64_t instance) {
        if(instance) for(auto& item:slots_) if(item.instance==instance) return &item;
        return nullptr;
    }
public:
    ButtonDelegatePool() { for(auto& item:slots_) item.binding.emplace(queue_); }
    ButtonDelegatePool(const ButtonDelegatePool&)=delete;
    ButtonDelegatePool& operator=(const ButtonDelegatePool&)=delete;
    bool open(uint64_t session) {
        if(session_ || closing_ || protects_owner() || !queue_.open(session)) return false;
        session_=session; return true;
    }
    bool protects_owner() const {
        for(const auto& item:slots_) if(item.binding->protects_owner()) return true;
        return false;
    }
    Binding* find(uint64_t instance) {
        auto* item=slot(instance);
        return item ? &*item->binding : nullptr;
    }
    void quarantine() {
        closing_=true;
        queue_.close(); // Revoke every queued/in-flight ticket before any release.
        for(auto& item:slots_) if(item.instance) item.binding->quarantine();
    }
    template<class Ops>
    ButtonDelegateResult install(Ops& ops,uint64_t session,uint64_t owner,uint64_t action,
                                 uint64_t instance,uint64_t original,uint64_t shadow) {
        if(!session_ || session!=session_ || closing_ || !instance) return ButtonDelegateResult::Invalid;
        if(!ops.on_thread()) return ButtonDelegateResult::Deferred;
        if(ops.faulted()) { quarantine(); return ButtonDelegateResult::Quarantined; }
        if(slot(instance)) return ButtonDelegateResult::Busy;
        for(auto& item:slots_) if(!item.instance) {
            item.instance=instance; // Publish lookup before a thunk can execute.
            auto result=item.binding->install(ops,session,owner,action,instance,original,shadow);
            if(!item.binding->protects_owner()) item.instance=0;
            return result;
        }
        return ButtonDelegateResult::Busy;
    }
    template<class Ops>
    ButtonDelegateResult remove(Ops& ops,uint64_t session,uint64_t instance) {
        if(!session_ || session!=session_) return ButtonDelegateResult::Invalid;
        if(!ops.on_thread()) return ButtonDelegateResult::Deferred;
        if(ops.faulted()) { quarantine(); return ButtonDelegateResult::Quarantined; }
        auto* item=slot(instance);
        if(!item) return ButtonDelegateResult::Invalid;
        auto result=item->binding->close(ops);
        if(result==ButtonDelegateResult::Ok) item->instance=0;
        return result;
    }
    // Factory supplies validation/exchange operations for each stable instance.
    // Close revokes the whole queue first, even if one control is still executing.
    template<class Factory>
    ButtonDelegateResult close(Factory&& factory) {
        if(!session_) return ButtonDelegateResult::Ok;
        for(const auto& item:slots_) if(item.instance) {
            auto ops=factory(item.instance);
            if(!ops.on_thread()) return ButtonDelegateResult::Deferred;
            if(ops.faulted()) { quarantine(); return ButtonDelegateResult::Quarantined; }
        }
        closing_=true; queue_.close();
        auto overall=ButtonDelegateResult::Ok;
        for(auto& item:slots_) if(item.instance) {
            auto ops=factory(item.instance);
            auto result=remove(ops,session_,item.instance);
            if(result==ButtonDelegateResult::Quarantined) overall=result;
            else if(result!=ButtonDelegateResult::Ok && overall==ButtonDelegateResult::Ok) overall=result;
        }
        if(overall==ButtonDelegateResult::Ok) { session_=0; closing_=false; }
        return overall;
    }
    bool pop(uint64_t session,MenuActionEvent& event) { return queue_.pop(session,event); }
    uint64_t take_dropped(uint64_t session) { return queue_.take_dropped(session); }
    MenuActionTicket ticket(uint64_t instance) const { return queue_.begin(instance); }
};
