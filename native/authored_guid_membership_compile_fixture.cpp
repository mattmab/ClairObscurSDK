#define NOMINMAX
#include <windows.h>
#include "target_authored_binding_query.h"
#include "authored_guid_membership.h"

template bool authored_guid_membership<TargetAuthoredBindingQuery<StrongLeasePool<>>>(
    TargetAuthoredBindingQuery<StrongLeasePool<>>&,const CallIdentity&,const uint32_t (&)[4]);
int main() {return 0;}
