#pragma once
#include "target_button_reference.h"
#include "button_delegate_forward.h"

// Candidate target adapter. The containing runtime must first verify the exact
// executable fingerprint. Store this object in module static storage: module
// lookup intentionally rejects stack/heap shadow tables. Once ready, base,
// entries, original callbacks and thread are never reset or replaced.
class TargetButtonDelegateTable {
    ButtonDelegateContract::Table shadow_{};
    uint64_t base_=0;
    DWORD thread_=0;
    volatile LONG fault_=0;
    bool ready_=false;
    static HMODULE module_at(uint64_t address) {
        HMODULE module=nullptr;
        if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                              GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                              reinterpret_cast<LPCWSTR>(address),&module)) return nullptr;
        return module;
    }
public:
    TargetButtonDelegateTable()=default;
    TargetButtonDelegateTable(const TargetButtonDelegateTable&)=delete;
    TargetButtonDelegateTable& operator=(const TargetButtonDelegateTable&)=delete;
    bool initialize(uint64_t base,ButtonDelegateContract::Destroy destroy,
                    ButtonDelegateContract::Execute execute,ButtonDelegateContract::ExecuteIfSafe safe) {
        if(ready_) return base_==base && on_thread() && !faulted() &&
            shadow_[0]==reinterpret_cast<uint64_t>(destroy) &&
            shadow_[11]==reinterpret_cast<uint64_t>(execute) &&
            shadow_[12]==reinterpret_cast<uint64_t>(safe);
        if(!base || faulted() || !TargetButtonReferenceOps{base}.can_release()) return false;
        ButtonDelegateContract::Table observed{}, prepared{};
        for(size_t i=0;i<observed.size();++i)
            observed[i]=local_read<uint64_t>(base+ButtonDelegateContract::table_rva+i*8);
        if(!ButtonDelegateContract::prepare(base,observed,prepared,destroy,execute,safe)) return false;
        const auto module=module_at(reinterpret_cast<uint64_t>(this));
        if(!module || module_at(reinterpret_cast<uint64_t>(shadow_.data()))!=module ||
           module_at(reinterpret_cast<uint64_t>(destroy))!=module ||
           module_at(reinterpret_cast<uint64_t>(execute))!=module ||
           module_at(reinterpret_cast<uint64_t>(safe))!=module) return false;
        HMODULE pinned=nullptr;
        if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_PIN,
                              reinterpret_cast<LPCWSTR>(this),&pinned) || pinned!=module) return false;
        shadow_=prepared; base_=base; thread_=GetCurrentThreadId(); ready_=true;
        return true;
    }
    bool ready() const { return ready_; }
    bool on_thread() const { return ready_ && GetCurrentThreadId()==thread_; }
    bool faulted() { return InterlockedCompareExchange(&fault_,0,0)!=0; }
    void foreign_call() { InterlockedExchange(&fault_,1); }
    uint64_t base() const { return base_; }
    uint64_t original_table() const { return base_+ButtonDelegateContract::table_rva; }
    uint64_t shadow_table() const { return reinterpret_cast<uint64_t>(shadow_.data()); }
    ButtonDelegateContract::Execute execute() const {
        return reinterpret_cast<ButtonDelegateContract::Execute>(base_+0x3059490);
    }
    ButtonDelegateContract::ExecuteIfSafe execute_if_safe() const {
        return reinterpret_cast<ButtonDelegateContract::ExecuteIfSafe>(base_+0x305a2e0);
    }
    ButtonDelegateContract::Destroy destroy() const {
        return reinterpret_cast<ButtonDelegateContract::Destroy>(base_+0x1260100);
    }
    bool original_unchanged() const {
        if(!ready_) return false;
        ButtonDelegateContract::Table observed{};
        for(size_t i=0;i<observed.size();++i) observed[i]=local_read<uint64_t>(original_table()+i*8);
        return ButtonDelegateContract::matches(base_,observed);
    }
};

struct TargetButtonDelegateOps {
    TargetButtonDelegateTable& table;
    TargetButtonReference& retained;
    bool on_thread() const { return table.on_thread(); }
    bool faulted() { return table.faulted(); }
    void foreign_call() { table.foreign_call(); }
    bool validate(uint64_t instance,uint64_t expected_table,uint64_t shadow) {
        return on_thread() && !faulted() && instance>=0x10000 && !(instance&7) &&
            expected_table==table.original_table() && shadow==table.shadow_table() &&
            retained.slate.state==SlateReferenceState::Live && instance==retained.delegate &&
            table.original_unchanged() && retained.unchanged(table.base());
    }
    uint64_t exchange(uint64_t instance,uint64_t next,uint64_t expected) {
        // This method is also used immediately before destruction. Do not read
        // the UObject or demand GC inactivity here: the caller owns the retained
        // SButton, and the destructor callback itself proves its instance exists.
        // Outer lifecycle SEH quarantines any unexpected stale-memory access.
        if(!on_thread() || faulted() || instance<0x10000 || (instance&7) ||
           instance!=retained.delegate || retained.slate.state!=SlateReferenceState::Live ||
           !((next==table.shadow_table() && expected==table.original_table()) ||
             (next==table.original_table() && expected==table.shadow_table()))) return 0;
        return reinterpret_cast<uint64_t>(InterlockedCompareExchangePointer(
            reinterpret_cast<void* volatile*>(instance),reinterpret_cast<void*>(next),
            reinterpret_cast<void*>(expected)));
    }
};

