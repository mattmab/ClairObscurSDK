#include "scavenger_repeat_guard.h"
#include <cassert>
#include <stdexcept>
#include <iostream>
struct RepeatOps {
    uint8_t repeat=0,audio=0;bool identity=true,fail_second_once=false;unsigned writes=0;
    bool valid()const{return identity;}
    bool read(uint8_t& first,uint8_t& second)const {first=repeat;second=audio;return true;}
    void write(uint8_t first,uint8_t second) {
        ++writes;repeat=first;
        if(fail_second_once){fail_second_once=false;throw std::runtime_error("second byte");}
        ++writes;audio=second;
    }
};
int main() {
    for(uint8_t original_repeat:{uint8_t(0),uint8_t(1)})for(uint8_t original_audio:{uint8_t(0),uint8_t(1)}) {
        RepeatOps ops;ops.repeat=original_repeat;ops.audio=original_audio;ScavengerRepeatGuard guard;
        assert(guard.prepare(ops));guard.apply(ops);assert(ops.repeat==1&&ops.audio==1);
        assert(guard.restore(ops)&&ops.repeat==original_repeat&&ops.audio==original_audio&&ops.writes==4);
        assert(guard.restore(ops)&&ops.writes==4);
    }
    for(unsigned invalid=0;invalid<2;++invalid) {
        RepeatOps ops;if(invalid)ops.audio=2;else ops.repeat=2;
        ScavengerRepeatGuard guard;assert(!guard.prepare(ops)&&ops.writes==0);
    }
    {RepeatOps ops;ops.identity=false;ScavengerRepeatGuard guard;assert(!guard.prepare(ops)&&ops.writes==0);}
    {RepeatOps ops;ScavengerRepeatGuard guard;assert(guard.prepare(ops));
     try{guard.apply(ops);throw std::runtime_error("dispatch");}catch(const std::runtime_error&){assert(guard.restore(ops));}
     assert(ops.repeat==0&&ops.audio==0&&ops.writes==4);}
    {RepeatOps ops;ops.fail_second_once=true;ScavengerRepeatGuard guard;assert(guard.prepare(ops));
     try{guard.apply(ops);assert(false);}catch(const std::runtime_error&){assert(guard.restore(ops));}
     assert(ops.repeat==0&&ops.audio==0&&ops.writes==3);}
    {RepeatOps ops;ScavengerRepeatGuard guard;assert(guard.prepare(ops));guard.apply(ops);ops.identity=false;
     assert(!guard.restore(ops)&&ops.writes==2&&!guard.restored);}
    {RepeatOps ops;ScavengerRepeatGuard guard;assert(guard.restore(ops)&&ops.writes==0);}
    std::cout<<"Scoped Scavenger repeat/audio source restoration fixtures passed\n";
}
