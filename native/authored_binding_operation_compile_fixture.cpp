#define NOMINMAX
#include <windows.h>
#include "target_authored_binding_operation.h"

// Instantiate the real retained operation; engine dispatch requires a live
// target, so ordinary fixture execution never enters this branch.
bool factory(void*,uint64_t,const CallIdentity&,const CallIdentity&,const CallIdentity&) {return false;}
int main() {
    StrongLeasePool<8> proof;
    e33_authored_binding::PortableInputs inputs{};
    int owner=0;
    TargetAuthoredBindingOperation<StrongLeasePool<8>> operation(0,0,proof,{},{},{},0,0,0,inputs,&owner,factory);
    const uint32_t guid[4]{1,2,3,4};
    const auto result=operation.run(guid);
    uint32_t count=0;(void)operation.identities(count);
    (void)operation.close();
    return result==e33_camera_binding::QueryResult::rejected && !operation.active() && !operation.uncertain() &&
        !count && operation.close()==e33_camera_binding::QueryResult::ok ? 0 : 1;
}
