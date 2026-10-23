#include "retired_owned_actor.h"
#include <cassert>
int main(){
    using e33_owned_actor::externally_retired;
    assert(externally_retired(true,true,true,true,true,true));
    // A changed world, dead-looking pointer or destruction marker cannot
    // replace any of the independent ownership/context checks.
    for(unsigned mask=0;mask<63;++mask)
        assert(!externally_retired(mask&1,mask&2,mask&4,mask&8,mask&16,mask&32));
    assert(e33_owned_actor::purged(true,true,true,true));
    for(unsigned mask=0;mask<15;++mask)
        assert(!e33_owned_actor::purged(mask&1,mask&2,mask&4,mask&8));
    return 0;
}
