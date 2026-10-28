#define NOMINMAX
#include <windows.h>
#include "target_authored_binding_authority.h"

// Compile the real reader, proof, resolver and authority as a single adapter.
// These methods require a live engine base; do not execute this dead branch.
using Pool=StrongLeasePool<8>;
using Query=TargetAuthoredBindingQuery<Pool>;
using Ops=TargetAuthoredBindingAuthorityOps<Query,Pool>;
bool owns(void*,const CallIdentity&,const CallIdentity&,const CallIdentity&) {return false;}
bool approved(void*,const e33_camera_binding::BindingValue&) {return false;}
bool epoch(void*,uint64_t,const CallIdentity&,const CallIdentity&,const CallIdentity&) {return false;}
bool released(void*) {return true;}
int main(int argc,char**) {
    if(argc==1)return 0;
    Pool leases,outputs;
    Query query{0,0,{},{},{},{},outputs,nullptr,owns,approved};
    e33_authored_binding::PortableInputs input{};
    int owner=0;
    Ops ops(query,leases,input,{},{},0,0,&owner,epoch,released);
    e33_authored_binding::Authority<CallIdentity> authority;
    const uint32_t guid[4]{1,2,3,4};
    if(authority.derive(ops,1,{},{},{},{},guid))return 1;
    e33_camera_binding::BindingValue value{};
    if(authority.matches(ops,1,{},{},{},value))return 2;
    return 0;
}
