#pragma once
#include "target_button_delegate.h"

// One menu button in the current native menu contract. Storage, table and thunk
// owner are module-static and never moved. Multi-control routing can extend this
// owner after the isolated one-button runtime is proven live.
class TargetButtonActions {
    using Queue=MenuActionEvents<>;
    using Binding=OwnedButtonDelegate<Queue>;
    using Forward=ButtonDelegateForward<Binding,TargetButtonDelegateOps>;
    TargetButtonDelegateTable table_;
    Queue queue_;
    Binding binding_{queue_};
    TargetButtonReference* retained_=nullptr;
    uint64_t session_=0;
    static inline void* volatile published_=nullptr;
    static TargetButtonActions& owner() {
        return *static_cast<TargetButtonActions*>(InterlockedCompareExchangePointer(&published_,nullptr,nullptr));
    }
    static void* execute(void* instance,void* reply) {
        auto& self=owner();
        TargetButtonDelegateOps ops{self.table_,*self.retained_};
        return Forward::execute(self.binding_,ops,self.table_.execute(),instance,reply);
    }
    static bool execute_safe(void* instance) {
        auto& self=owner();
        TargetButtonDelegateOps ops{self.table_,*self.retained_};
        return Forward::execute_if_safe(self.binding_,ops,self.table_.execute_if_safe(),instance);
    }
    static void* destroy(void* instance,uint32_t flags) {
        auto& self=owner();
        TargetButtonDelegateOps ops{self.table_,*self.retained_};
        return Forward::destroy(self.binding_,ops,self.table_.destroy(),instance,flags);
    }
public:
    TargetButtonActions()=default;
    TargetButtonActions(const TargetButtonActions&)=delete;
    TargetButtonActions& operator=(const TargetButtonActions&)=delete;
    bool protects_owner() const { return binding_.protects_owner(); }
    void quarantine() { if(table_.ready()) binding_.quarantine(); }
    ButtonDelegateResult gate() {
        if(!table_.ready()) return ButtonDelegateResult::Ok;
        TargetButtonDelegateOps ops{table_,*retained_};
        return button_delegate_control_gate(binding_,ops);
    }
    ButtonDelegateResult bind(uint64_t base,uint64_t session,uint64_t mod_owner,uint64_t action,
                              TargetButtonReference& retained) {
        if(!session || !mod_owner || !action || (retained_ && retained_!=&retained))
            return ButtonDelegateResult::Invalid;
        if(!table_.initialize(base,destroy,execute,execute_safe)) return ButtonDelegateResult::Invalid;
        // Initialize the stable reference before publishing. A second owner in
        // this module is rejected; old thunks can never attach to a replacement.
        if(!retained_) retained_=&retained;
        auto previous=InterlockedCompareExchangePointer(&published_,this,nullptr);
        if(previous && previous!=this) return ButtonDelegateResult::Invalid;
        auto allowed=gate(); if(allowed!=ButtonDelegateResult::Ok) return allowed;
        if(session_ && session_!=session) return ButtonDelegateResult::Busy;
        if(!session_) {
            if(!queue_.open(session)) return ButtonDelegateResult::Invalid;
            session_=session;
        }
        TargetButtonDelegateOps ops{table_,retained};
        return binding_.install(ops,session,mod_owner,action,retained.delegate,
                                table_.original_table(),table_.shadow_table());
    }
    ButtonDelegateResult close() {
        auto allowed=gate(); if(allowed!=ButtonDelegateResult::Ok) return allowed;
        if(!table_.ready()) return ButtonDelegateResult::Ok;
        TargetButtonDelegateOps ops{table_,*retained_};
        auto result=binding_.close(ops);
        if(result==ButtonDelegateResult::Ok) { queue_.close(); session_=0; }
        return result;
    }
    ButtonDelegateResult drain(uint64_t session,MenuActionEvent* output,size_t capacity,
                               size_t& count,uint64_t& dropped) {
        count=0; dropped=0;
        auto allowed=gate(); if(allowed!=ButtonDelegateResult::Ok) return allowed;
        if(!session || session!=session_ || !output || !capacity || capacity>64)
            return ButtonDelegateResult::Invalid;
        while(count<capacity && queue_.pop(session,output[count])) ++count;
        dropped=queue_.take_dropped(session);
        return ButtonDelegateResult::Ok;
    }
};
