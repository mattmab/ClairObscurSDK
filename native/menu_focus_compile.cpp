#include "target_menu_focus.h"
SlateReferenceResult compile_menu_capture(TargetMenuFocusOwner& owner,uint64_t base,const CallIdentity& engine) {
    return owner.capture(base,engine);
}
bool compile_menu_observe(TargetMenuFocusOwner& owner,uint64_t base,TargetMenuFocusSnapshot& snapshot) {
    return owner.observe(base,snapshot);
}
SlateReferenceResult compile_menu_release(TargetMenuFocusOwner& owner,uint64_t base) {
    return owner.release(base);
}
