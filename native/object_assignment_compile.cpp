// Compile target bindings without running them or replacing any loaded DLL.
#include "target_object_assignment.h"
ObjectAssignmentResult compile_object_assignment(TargetObjectAssignmentOps& ops,ObjectAssignment& r) {
    return assign_object_property(ops,r);
}
