#pragma once
#include "cinematic_animation_drain.h"
#include <cstdint>
#include <cstddef>
namespace e33_cinematic {
// Build 23765773 only. Caller must validate the exact title class/native finish
// virtual, reflected arrays, retained identities and game-thread ownership.
// Call after the captured animation was unbound/stopped once. A captured player
// is kept alive independently of the widget arrays. Stopped status alone is
// insufficient: completion/root teardown must have cleared the stopping bit,
// linker, shared state and reference controller. The fourth root word is NOT
// required zero: native teardown does not clear it. No clock/frame assumption.
template<class Reader>
AnimationQuiescence title_animation_quiescence(Reader&& read,uint64_t widget,
                                              uint64_t player) {
    if(!widget || widget>UINT64_MAX-600) return AnimationQuiescence::uncertain;
    bool pending=false;
    for(uint64_t offset:{uint64_t(544),uint64_t(560),uint64_t(584)}) {
        uint64_t data{};int32_t count{},capacity{};
        if(!read(widget+offset,&data,sizeof(data)) ||
           !read(widget+offset+8,&count,sizeof(count)) ||
           !read(widget+offset+12,&capacity,sizeof(capacity)) ||
           count<0 || capacity<count || capacity>64 ||
           (capacity && (!data || (data&7)))) return AnimationQuiescence::uncertain;
        if(count) pending=true;
    }
    if(player) {
        if(player>UINT64_MAX-0x2ae) return AnimationQuiescence::uncertain;
        int32_t status{};uint8_t flags{};uint64_t linker{},shared{},controller{};
        if(!read(player+0x274,&status,4) || !read(player+0x2ad,&flags,1) ||
           !read(player+0x220,&linker,8) || !read(player+0x228,&shared,8) ||
           !read(player+0x230,&controller,8))
            return AnimationQuiescence::uncertain;
        if(status || (flags&1) || linker || shared || controller) pending=true;
    }
    return pending ? AnimationQuiescence::pending : AnimationQuiescence::complete;
}
}
