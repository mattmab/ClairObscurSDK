#include "keybind_protocol.h"
#include <cassert>
#include <cstdio>
#include <initializer_list>
using namespace e33_keys;
static Packet request(uint32_t operation, uint64_t generation) {
    Packet p; p.session=123; p.operation=operation; p.generation=generation; return p;
}
int main() {
    State s; s.begin(123);
    auto p=request(Replace,1); p.count=1; p.bindings[0]={1,117};
    assert(valid_request(p)); s.command(p,0); assert(!p.error);
    s.press(117,true,true); s.press(117,false,false); s.press(118,false,true);
    auto drain=request(Drain,1); s.command(drain,0); assert(!drain.error && !drain.count);
    s.press(117,false,true); drain=request(Drain,1); s.command(drain,0);
    assert(drain.count==1 && drain.bindings[0].token==1 && drain.bindings[0].key==117);
    drain=request(Drain,1); s.command(drain,0); assert(!drain.count);
    s.press(117,false,true);
    auto next=request(Replace,2); next.count=1; next.bindings[0]={2,118}; s.command(next,0);
    drain=request(Drain,2); s.command(drain,0); assert(!drain.count); // Old queue revoked.
    s.command(p,0); assert(p.error==2); // No generation rollback.
    auto reserved=request(Replace,3); reserved.count=1; reserved.bindings[0]={3,119};
    s.command(reserved,119); assert(reserved.error==3 && s.contains(118));
    auto duplicate=request(Replace,3); duplicate.count=2; duplicate.bindings[0]={1,117}; duplicate.bindings[1]={2,117};
    assert(!valid_request(duplicate));
    auto wrong=request(Drain,2); wrong.session=456; s.command(wrong,0); assert(wrong.error);
    for(uint32_t i=0;i<capacity+6;++i) s.press(118,false,true);
    drain=request(Drain,2); s.command(drain,0); assert(drain.count==capacity && drain.dropped==6);
    for(uint32_t i=0;i<capacity;++i) assert(drain.bindings[i].token==2 && drain.bindings[i].key==118);
    auto capture=request(Capture,3);capture.count=1;capture.bindings[0]={3,65};
    s.command(capture,0);assert(!capture.error && s.capturing());
    s.press(65,true,true);drain=request(Drain,3);s.command(drain,0);assert(!drain.count);
    s.press(65,false,true);drain=request(Drain,3);s.command(drain,0);assert(drain.count==1);
    auto restored=request(Replace,4);s.command(restored,0);assert(!s.capturing());
    for(uint32_t key : {188u,190u}) {
        auto punctuation=request(Capture,key);punctuation.count=1;punctuation.bindings[0]={1,key};
        s.command(punctuation,0);assert(!punctuation.error);
        s.press(key,false,true);auto result=request(Drain,key);s.command(result,0);
        assert(result.count==1 && result.bindings[0].key==key);
    }
    s.close(); s.press(118,false,true); drain=request(Drain,4); s.command(drain,0); assert(drain.error);
    s.begin(999); wrong=request(Replace,4); s.command(wrong,0); assert(wrong.error);
    assert(!supported_key(192)); assert(!supported_key(0)); // Console tilde / invalid.
    std::puts("keybind ABI, filtering, generations, overflow and cleanup: PASS");
}
