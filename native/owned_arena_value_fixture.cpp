#include "owned_arena_value.h"
#include <cassert>
#include <cstring>
#include <stdexcept>
#include <cstdio>

int main(){
    using namespace e33_enemy_spawn;
    OwnedArenaValue value;unsigned copies=0;uint8_t source[40]{};source[8]=7;
    auto copy=[&](void* to,const void* from){++copies;std::memcpy(to,from,40);};
    assert(value.assign(copy,source)&&value.live&&copies==1);
    assert(!value.assign(copy,source)&&copies==1);
    assert(!value.close([](){return false;},copy)&&value.live&&copies==1);
    assert(value.close([](){return true;},copy)&&!value.live&&copies==2&&value.bytes[8]==0);
    assert(value.close([](){return false;},copy)&&copies==2);
    OwnedArenaValue unknown;
    volatile bool fail=true;
    try{unknown.assign([&](void*,const void*){if(fail)throw std::runtime_error("copy");},source);assert(false);}catch(const std::runtime_error&){}
    assert(unknown.live&&!unknown.assign(copy,source));
    try{unknown.close([](){return true;},[&](void*,const void*){if(fail)throw std::runtime_error("clear");});assert(false);}catch(const std::runtime_error&){}
    assert(unknown.live);
    assert(unknown.close([](){return true;},copy)&&!unknown.live);
    puts("Owned arena value fixture passed: once-only assign, failed preflight retention, independent close, exception journal.");
}
