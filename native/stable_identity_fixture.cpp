#include "stable_identity.h"
#include <cassert>
#include <cstdio>

struct Ops {
    CallIdentity current{42,0,0x10000};
    bool allowed=true, lose_context=false, mismatch=false, replace=false;
    int32_t result=1001;
    unsigned allocations=0;
    bool can_assign() const { return allowed; }
    CallIdentity capture(uint64_t) const { return current; }
    int32_t allocate_serial(int32_t index) {
        assert(index==42); ++allocations;
        current.serial=mismatch ? result+1 : result;
        if(replace) current.index=43;
        if(lose_context) allowed=false;
        return result;
    }
};
int main() {
    {
        Ops ops; auto id=ops.current;
        assert(stabilize_retained_identity(ops,id));
        assert(id.serial==1001 && ops.allocations==1);
        assert(stabilize_retained_identity(ops,id) && ops.allocations==1);
    }
    {
        Ops ops; ops.current.serial=84711; auto id=ops.current;
        assert(stabilize_retained_identity(ops,id) && ops.allocations==0);
    }
    {
        Ops ops; auto id=ops.current; ops.current.serial=1002;
        assert(!stabilize_retained_identity(ops,id) && !ops.allocations && id.serial==0);
    }
    for(unsigned failure=0;failure<6;++failure) {
        Ops ops; auto id=ops.current;
        switch(failure) {
        case 0: ops.allowed=false; break;
        case 1: ops.lose_context=true; break;
        case 2: ops.mismatch=true; break;
        case 3: ops.replace=true; break;
        case 4: ops.result=0; break;
        case 5: ops.result=-1; break;
        }
        assert(!stabilize_retained_identity(ops,id));
        assert(id.serial==0); // Failed stabilization never publishes a new identity.
    }
    {
        Ops ops; auto id=ops.current; id.index=-1;
        assert(!stabilize_retained_identity(ops,id) && !ops.allocations);
        id=ops.current; id.address=0;
        assert(!stabilize_retained_identity(ops,id) && !ops.allocations);
        id=ops.current; id.serial=-1;
        assert(!stabilize_retained_identity(ops,id) && !ops.allocations);
    }
    std::puts("Stable identity: assignment, existing serial, stale zero, context loss, mismatch, replacement and invalid identities passed.");
}
