#pragma once
#include <cstdint>
#include <cstddef>
namespace e33_cinematic {
// Exact FWidgetAnimationBinding layout verified by native UserWidget
// UnbindAllFromAnimationFinished body 0x3113490: stride40, animation+0,
// event type+24 (finished=1). Caller validates the reflected array/class and
// both retained UObject identities; reads remain inside this bounded array.
template<class Reader>
bool title_finished_callbacks_absent(Reader&& read,uint64_t widget,uint64_t animation) {
    if(!widget || !animation || widget>UINT64_MAX-712) return false;
    uint64_t data{};int32_t count{},capacity{};
    if(!read(widget+696,&data,8) || !read(widget+704,&count,4) || !read(widget+708,&capacity,4) ||
       count<0 || capacity<count || capacity>64 || (count && (!data || (data&7))) ||
       data>UINT64_MAX-uint64_t(capacity)*40) return false;
    for(int32_t i=0;i<count;++i) {
        uint64_t bound{};uint8_t type{};
        const auto at=data+uint64_t(i)*40;
        if(!read(at,&bound,8) || !read(at+24,&type,1)) return false;
        if(bound==animation && type==1) return false;
    }
    return true;
}
}
