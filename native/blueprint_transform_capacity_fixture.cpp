#include "blueprint_argument_transform.h"
#include <cassert>

static e33_blueprint_transform::Decision begin(void*,uint64_t,void*,void*){return {};}
static void end(void*,uint64_t){}

int main(){
    // Existing story owners and the complete character execution/effect set must
    // coexist, and detaching that set must not disturb the other owners.
    int story=1,character=2,other=3;
    for(uint64_t function=1;function<=8;++function)
        assert(e33_blueprint_transform::attach(&story,function,begin,end));
    for(uint64_t function=9;function<=28;++function)
        assert(e33_blueprint_transform::attach(&character,function,begin,end));
    assert(!e33_blueprint_transform::attach(&other,9,begin,end));
    for(uint64_t function=29;function<=64;++function)
        assert(e33_blueprint_transform::attach(&other,function,begin,end));
    assert(!e33_blueprint_transform::attach(&other,65,begin,end));
    assert(e33_blueprint_transform::detach(&character));
    for(uint64_t function=1;function<=8;++function)
        assert(e33_blueprint_transform::find(function).owner==&story);
    for(uint64_t function=9;function<=28;++function)
        assert(!e33_blueprint_transform::selected(function));
    assert(e33_blueprint_transform::attach(&character,65,begin,end));
    assert(e33_blueprint_transform::detach(&character));
    assert(e33_blueprint_transform::detach(&story));
    assert(e33_blueprint_transform::detach(&other));
    return 0;
}
