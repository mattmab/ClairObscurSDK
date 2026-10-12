#include <cassert>
#include <iostream>
#include "media_owner_protocol.h"
struct Ops {
    unsigned calls[2]{};
    uint32_t deferred=0,failed=0;
    uint32_t invoke(uint32_t step) {
        ++calls[step];
        if(deferred) { --deferred; return 407; }
        return failed ? 1403 : 0;
    }
};
int main() {
    MediaCleanupState s; Ops o;
    s.state=1; o.deferred=1;
    assert(s.close(o)==407 && s.state==1 && s.step==0);
    assert(s.close(o)==0 && !s.state && s.step==2);
    assert(o.calls[0]==2 && o.calls[1]==1);
    assert(s.close(o)==0 && o.calls[1]==1);
    MediaCleanupState bad; Ops fail;
    bad.state=1; fail.failed=1;
    assert(bad.close(fail)==1403 && bad.state==2);
    assert(bad.close(fail)==1403 && fail.calls[0]==1 && !fail.calls[1]);
    std::cout << "media cleanup: ordered close/detach, deferred GC, quarantine/no retry PASS\n";
}
