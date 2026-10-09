#include "target_button_delegate.h"
#include "target_button_actions.h"
#include "target_multi_button_actions.h"

static TargetMultiButtonActions multi_actions;
ButtonDelegateResult compile_multi_bind(uint64_t base,uint64_t session,uint64_t owner,uint64_t action,
                                       uint64_t lease,const CallIdentity& identity) {
    return multi_actions.bind(base,session,owner,action,lease,identity);
}
ButtonDelegateResult compile_multi_close() { return multi_actions.close(); }
ButtonDelegateResult compile_multi_remove(uint64_t session,uint64_t lease) {
    return multi_actions.remove(session,lease);
}
ButtonDelegateResult compile_multi_drain(uint64_t session,MenuActionEvent* events,size_t& count,uint64_t& dropped) {
    return multi_actions.drain(session,events,64,count,dropped);
}

static TargetButtonDelegateTable target_table;
static TargetButtonActions target_actions;
ButtonDelegateResult compile_action_binding(uint64_t base,uint64_t session,uint64_t owner,uint64_t action,
                                            TargetButtonReference& retained) {
    return target_actions.bind(base,session,owner,action,retained);
}
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
