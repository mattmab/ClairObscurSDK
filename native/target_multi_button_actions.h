#pragma once
#include "target_button_delegate.h"
#include "button_delegate_pool.h"

// Candidate only. Caller verifies fingerprint, menu ownership and every UObject
// lease before bind, gates all control on the game thread, and contains SEH with
// quarantine(). Module-static storage and retained UObject leases outlive all
// entries, including failed acquisition/release. No v16 integration.
class TargetMultiButtonActions {
    static constexpr size_t Capacity=16;
    using Pool=ButtonDelegatePool<Capacity>;
    using Forward=ButtonDelegateForward<Pool::Binding,TargetButtonDelegateOps>;
    struct Control { uint64_t lease=0; TargetButtonReference retained; };
    TargetButtonDelegateTable table_;
    Pool pool_;
    std::array<Control,Capacity> controls_{};
    uint64_t session_=0;
    bool closing_=false;
    static inline void* volatile published_=nullptr;
    static TargetMultiButtonActions& owner() {
        return *static_cast<TargetMultiButtonActions*>(InterlockedCompareExchangePointer(&published_,nullptr,nullptr));
    }
    Control* instance(uint64_t address) {
        for(auto& c:controls_) if(c.lease && c.retained.delegate==address) return &c;
        return nullptr;
    }
    Control* control(uint64_t lease) {
        for(auto& c:controls_) if(c.lease==lease && lease) return &c;
        return nullptr;
    }
    // Never inspect pool/reference state from a foreign callback thread.
    static bool routed(TargetMultiButtonActions& self,void* address,Control*& c,Pool::Binding*& b) {
        if(!self.table_.on_thread()) { self.table_.foreign_call(); return false; }
        if(self.table_.faulted()) { self.pool_.quarantine(); return false; }
        const auto id=reinterpret_cast<uint64_t>(address);
        c=self.instance(id); b=self.pool_.find(id);
        if(!c || !b) { self.table_.foreign_call(); self.pool_.quarantine(); return false; }
        if(b->state()==ButtonDelegateState::Quarantined) { self.quarantine(); return false; }
        return true;
    }
    static void* execute(void* address,void* reply) {
        auto& self=owner(); Control* c=nullptr; Pool::Binding* b=nullptr;
        if(!routed(self,address,c,b)) return self.table_.execute()(address,reply);
        TargetButtonDelegateOps ops{self.table_,c->retained};
        return Forward::execute(*b,ops,self.table_.execute(),address,reply);
    }
    static bool execute_safe(void* address) {
        auto& self=owner(); Control* c=nullptr; Pool::Binding* b=nullptr;
        if(!routed(self,address,c,b)) return self.table_.execute_if_safe()(address);
        TargetButtonDelegateOps ops{self.table_,c->retained};
        return Forward::execute_if_safe(*b,ops,self.table_.execute_if_safe(),address);
    }
    static void* destroy(void* address,uint32_t flags) {
        auto& self=owner(); Control* c=nullptr; Pool::Binding* b=nullptr;
        if(!routed(self,address,c,b)) return self.table_.destroy()(address,flags);
        TargetButtonDelegateOps ops{self.table_,c->retained};
        return Forward::destroy(*b,ops,self.table_.destroy(),address,flags);
    }
    ButtonDelegateResult release(Control& c) {
        auto result=c.retained.release(table_.base());
        if(result==SlateReferenceResult::Ok) { c.lease=0; return ButtonDelegateResult::Ok; }
        if(result==SlateReferenceResult::Deferred) return ButtonDelegateResult::Deferred;
        quarantine(); return ButtonDelegateResult::Quarantined;
    }
public:
    TargetMultiButtonActions()=default;
    TargetMultiButtonActions(const TargetMultiButtonActions&)=delete;
    TargetMultiButtonActions& operator=(const TargetMultiButtonActions&)=delete;
    bool protects_owner() const {
        if(pool_.protects_owner()) return true;
        for(const auto& c:controls_) if(c.lease) return true;
        return false;
    }
    bool protects_lease(uint64_t lease) const {
        for(const auto& c:controls_) if(lease && c.lease==lease) return true;
        return false;
    }
    ButtonDelegateState state(uint64_t lease) {
        auto* c=control(lease);
        if(!c) return ButtonDelegateState::Empty;
        auto* binding=pool_.find(c->retained.delegate);
        return binding ? binding->state() : ButtonDelegateState::Revoked;
    }
    uint64_t registration(uint64_t lease) {
        auto* c=control(lease);
        return c ? pool_.ticket(c->retained.delegate).registration : 0;
    }
    void quarantine() { closing_=true; table_.foreign_call(); pool_.quarantine(); }
    ButtonDelegateResult gate() {
        if(!table_.ready()) return ButtonDelegateResult::Ok;
        if(!table_.on_thread()) return ButtonDelegateResult::Deferred;
        if(table_.faulted()) { pool_.quarantine(); return ButtonDelegateResult::Quarantined; }
        for(const auto& c:controls_) if(c.lease) {
            auto* binding=pool_.find(c.retained.delegate);
            if(binding && binding->state()==ButtonDelegateState::Quarantined) {
                quarantine(); return ButtonDelegateResult::Quarantined;
            }
        }
        return ButtonDelegateResult::Ok;
    }
    ButtonDelegateResult bind(uint64_t base,uint64_t session,uint64_t menu_owner,uint64_t action,
                              uint64_t lease,const CallIdentity& identity) {
        if(!session || !menu_owner || !action || !lease || closing_) return ButtonDelegateResult::Invalid;
        if(!table_.initialize(base,destroy,execute,execute_safe)) return ButtonDelegateResult::Invalid;
        auto prior=InterlockedCompareExchangePointer(&published_,this,nullptr);
        if(prior && prior!=this) return ButtonDelegateResult::Invalid;
        auto allowed=gate(); if(allowed!=ButtonDelegateResult::Ok) return allowed;
        if(session_ && session_!=session) return ButtonDelegateResult::Busy;
        if(!session_) { if(!pool_.open(session)) return ButtonDelegateResult::Invalid; session_=session; }
        for(const auto& c:controls_) if(c.lease && (c.lease==lease ||
            c.retained.button.address==identity.address)) return ButtonDelegateResult::Busy;
        for(auto& c:controls_) if(!c.lease) {
            c.lease=lease; // Durable owner exists before acquiring a native ref.
            auto captured=c.retained.capture(base,identity);
            if(captured!=SlateReferenceResult::Ok) {
                if(c.retained.slate.state==SlateReferenceState::Empty) c.lease=0;
                else quarantine();
                return c.lease ? ButtonDelegateResult::Quarantined : ButtonDelegateResult::Invalid;
            }
            TargetButtonDelegateOps ops{table_,c.retained};
            auto result=pool_.install(ops,session,menu_owner,action,c.retained.delegate,
                                      table_.original_table(),table_.shadow_table());
            if(result!=ButtonDelegateResult::Ok && !pool_.find(c.retained.delegate)) {
                auto cleanup=release(c);
                if(cleanup!=ButtonDelegateResult::Ok) return cleanup;
            }
            return result;
        }
        return ButtonDelegateResult::Busy;
    }
    ButtonDelegateResult remove(uint64_t session,uint64_t lease) {
        auto allowed=gate(); if(allowed!=ButtonDelegateResult::Ok) return allowed;
        if(!session_ || session!=session_) return ButtonDelegateResult::Invalid;
        auto* c=control(lease); if(!c) return ButtonDelegateResult::Invalid;
        if(pool_.find(c->retained.delegate)) {
            TargetButtonDelegateOps ops{table_,c->retained};
            auto result=pool_.remove(ops,session,c->retained.delegate);
            if(result!=ButtonDelegateResult::Ok) return result;
        }
        return release(*c);
    }
    ButtonDelegateResult close() {
        auto allowed=gate(); if(allowed!=ButtonDelegateResult::Ok) return allowed;
        if(!session_) return ButtonDelegateResult::Ok;
        closing_=true;
        auto result=pool_.close([&](uint64_t id) {
            return TargetButtonDelegateOps{table_,instance(id)->retained};
        });
        if(result!=ButtonDelegateResult::Ok) return result;
        for(auto& c:controls_) if(c.lease) {
            result=release(c); if(result!=ButtonDelegateResult::Ok) return result;
        }
        session_=0; closing_=false; return ButtonDelegateResult::Ok;
    }
    ButtonDelegateResult drain(uint64_t session,MenuActionEvent* output,size_t capacity,
                               size_t& count,uint64_t& dropped) {
        count=0; dropped=0;
        auto allowed=gate(); if(allowed!=ButtonDelegateResult::Ok) return allowed;
        if(!session_ || session!=session_ || closing_ || !output || !capacity || capacity>64)
            return ButtonDelegateResult::Invalid;
        while(count<capacity && pool_.pop(session,output[count])) ++count;
        dropped=pool_.take_dropped(session); return ButtonDelegateResult::Ok;
    }
};
