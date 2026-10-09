// Compile the target adapter without executing it or touching a loaded DLL.
#include "target_strong_reference.h"
StrongReferenceResult compile_target_create(TargetStrongReferenceOps& ops,uint64_t object,
                                            StrongReferenceStorage& holder) {
    return create_strong_reference(ops,object,holder);
}
StrongReferenceResult compile_target_release(TargetStrongReferenceOps& ops,StrongReferenceStorage& holder) {
    return release_strong_reference(ops,holder);
}
