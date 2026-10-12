#include "cinematic_animation_callbacks.h"
#include <array>
#include <cassert>
#include <cstring>
#include <iostream>
int main() {
    using namespace e33_cinematic;
    constexpr uint64_t widget=0x10000,animation=0x30000,data=widget+1024;
    std::array<uint8_t,4096> memory{};
    auto read=[&](uint64_t at,void* out,size_t size) {
        if(at<widget || at-widget>memory.size() || size>memory.size()-(at-widget)) return false;
        std::memcpy(out,memory.data()+at-widget,size);return true;
    };
    int32_t count=2,capacity=2;
    std::memcpy(memory.data()+696,&data,8);std::memcpy(memory.data()+704,&count,4);
    std::memcpy(memory.data()+708,&capacity,4);
    std::memcpy(memory.data()+1024,&animation,8);memory[1024+24]=0; // Started may remain.
    uint64_t unrelated=animation+256;
    std::memcpy(memory.data()+1064,&unrelated,8);memory[1064+24]=1;
    assert(title_finished_callbacks_absent(read,widget,animation));
    memory[1024+24]=1;assert(!title_finished_callbacks_absent(read,widget,animation));
    memory[1024+24]=0;count=3;std::memcpy(memory.data()+704,&count,4);
    assert(!title_finished_callbacks_absent(read,widget,animation));
    assert(!title_finished_callbacks_absent(read,UINT64_MAX,animation));
    auto fail=[](uint64_t,void*,size_t){return false;};
    assert(!title_finished_callbacks_absent(fail,widget,animation));
    std::cout<<"Title animation callback filtering and bounded read checks passed\n";
}
