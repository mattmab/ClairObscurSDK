#include "target_button_delegate.h"

static TargetButtonDelegateTable target_table;
using TargetActionQueue=MenuActionEvents<>;
using TargetActionBinding=OwnedButtonDelegate<TargetActionQueue>;

bool compile_target_table(uint64_t base,ButtonDelegateContract::Destroy destructor,
                          ButtonDelegateContract::Execute execute,ButtonDelegateContract::ExecuteIfSafe safe) {
    return target_table.initialize(base,destructor,execute,safe);
}
ButtonDelegateResult compile_target_install(TargetActionBinding& binding,TargetButtonReference& retained,
                                            uint64_t session,uint64_t owner,uint64_t action) {
    TargetButtonDelegateOps operations{target_table,retained};
    auto gate=button_delegate_control_gate(binding,operations);
    if(gate!=ButtonDelegateResult::Ok) return gate;
    return binding.install(operations,session,owner,action,retained.delegate,
                           target_table.original_table(),target_table.shadow_table());
}
ButtonDelegateResult compile_target_close(TargetActionBinding& binding,TargetButtonReference& retained) {
    TargetButtonDelegateOps operations{target_table,retained};
    auto gate=button_delegate_control_gate(binding,operations);
    return gate==ButtonDelegateResult::Ok ? binding.close(operations) : gate;
}
void* compile_target_forward(TargetActionBinding& binding,TargetButtonReference& retained,void* instance,void* reply) {
    TargetButtonDelegateOps operations{target_table,retained};
    return ButtonDelegateForward<TargetActionBinding,TargetButtonDelegateOps>::execute(
        binding,operations,target_table.execute(),instance,reply);
}
bool compile_target_safe(TargetActionBinding& binding,TargetButtonReference& retained,void* instance) {
    TargetButtonDelegateOps operations{target_table,retained};
    return ButtonDelegateForward<TargetActionBinding,TargetButtonDelegateOps>::execute_if_safe(
        binding,operations,target_table.execute_if_safe(),instance);
}
void* compile_target_destroy(TargetActionBinding& binding,TargetButtonReference& retained,void* instance,uint32_t flags) {
    TargetButtonDelegateOps operations{target_table,retained};
    return ButtonDelegateForward<TargetActionBinding,TargetButtonDelegateOps>::destroy(
        binding,operations,target_table.destroy(),instance,flags);
}
