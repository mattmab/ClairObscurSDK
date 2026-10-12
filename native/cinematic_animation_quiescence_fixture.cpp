#include "cinematic_animation_quiescence.h"
#include <array>
#include <cassert>
#include <cstring>
#include <iostream>
int main() {
    using namespace e33_cinematic;
    constexpr uint64_t widget=0x10000,player=widget+2048;
    std::array<uint8_t,4096> memory{};
    auto read=[&](uint64_t address,void* value,size_t size) {
        if(address<widget || address-widget>memory.size() || size>memory.size()-(address-widget)) return false;
        std::memcpy(value,memory.data()+address-widget,size);return true;
    };
    auto count=[&](size_t offset,int32_t n,int32_t capacity=2) {
        uint64_t data=0x20000;
        std::memcpy(memory.data()+offset,&data,8);
        std::memcpy(memory.data()+offset+8,&n,4);
        std::memcpy(memory.data()+offset+12,&capacity,4);
    };
    assert(title_animation_quiescence(read,widget,0)==AnimationQuiescence::complete);
    assert(title_animation_quiescence(read,widget,player)==AnimationQuiescence::complete);
    for(size_t offset:{size_t(544),size_t(560),size_t(584)}) {
        count(offset,1);assert(title_animation_quiescence(read,widget,player)==AnimationQuiescence::pending);
        count(offset,0);assert(title_animation_quiescence(read,widget,player)==AnimationQuiescence::complete);
        count(offset,-1);assert(title_animation_quiescence(read,widget,player)==AnimationQuiescence::uncertain);
        count(offset,3);assert(title_animation_quiescence(read,widget,player)==AnimationQuiescence::uncertain);
        count(offset,0,65);assert(title_animation_quiescence(read,widget,player)==AnimationQuiescence::uncertain);
        count(offset,0);
    }
    for(size_t offset:{size_t(0x274),size_t(0x2ad),size_t(0x220),size_t(0x228),size_t(0x230)}) {
        memory[2048+offset]=1;
        assert(title_animation_quiescence(read,widget,player)==AnimationQuiescence::pending);
        memory[2048+offset]=0;
    }
    memory[2048+0x238]=0xff; // Native teardown deliberately leaves fourth root word.
    assert(title_animation_quiescence(read,widget,player)==AnimationQuiescence::complete);
    auto fail=[](uint64_t,void*,size_t){return false;};
    assert(title_animation_quiescence(fail,widget,player)==AnimationQuiescence::uncertain);
    assert(title_animation_quiescence(read,UINT64_MAX,player)==AnimationQuiescence::uncertain);
    std::cout<<"Title animation arrays, completion/root teardown and bounds checks passed\n";
}
