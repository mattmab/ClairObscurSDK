#include "target_menu_focus.h"
#include "target_menu_ops.h"
SlateReferenceResult compile_menu_capture(TargetMenuFocusOwner& owner,uint64_t base,const CallIdentity& engine) {
    return owner.capture(base,engine);
}
bool compile_menu_observe(TargetMenuFocusOwner& owner,uint64_t base,TargetMenuFocusSnapshot& snapshot) {
    return owner.observe(base,snapshot);
}
SlateReferenceResult compile_menu_release(TargetMenuFocusOwner& owner,uint64_t base) {
    return owner.release(base);
}
MenuResult compile_menu_operations(TargetMenuStorage& storage,StrongLeasePool<>& leases) {
    TargetMenuOps<StrongLeasePool<>> ops{storage,leases};
    auto result=storage.lifetime.register_owned(ops,storage.session,storage.owner,storage.widget_lease,storage.child_lease);
    if(result==MenuResult::Ok) result=storage.lifetime.attach(ops,storage.session,storage.owner);
    if(result==MenuResult::Ok) result=storage.lifetime.focus(ops,storage.session,storage.owner);
    if(result==MenuResult::Ok) result=storage.lifetime.close(ops,storage.session,storage.owner);
    return result;
}
