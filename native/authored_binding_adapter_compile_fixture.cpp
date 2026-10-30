#define NOMINMAX
#include <windows.h>
#include "target_authored_binding_query.h"

// The read-only research adapter is deliberately not connected to a session.
// Compiling this translation unit verifies its exact-build helper dependencies.
template struct TargetAuthoredBindingQuery<StrongLeasePool<>>;
int main() {return 0;}
