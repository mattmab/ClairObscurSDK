#include "damage_modifier_frame.h"
#include <array>
#include <cassert>
#include <cstdio>
#include <limits>
int main(){
    std::array<uint8_t,512> bytes{};
    auto put=[&](uint64_t at,uint64_t value){std::memcpy(bytes.data()+at-0x1000,&value,8);};
    auto read=[&](uint64_t at,void* out,uint32_t size){if(at<0x1000||at+size>0x1200)return false;std::memcpy(out,bytes.data()+at-0x1000,size);return true;};
    put(0x1010,1);put(0x1018,2);put(0x1020,3);put(0x1028,0x1100);put(0x1090,1);
    auto param=[&](bool direct=false){return e33_damage_evidence::parameter(read,0x1000,1,2,3,4,direct);};
    assert(param()==0x1100);assert(!param(true));put(0x1090,0);assert(param(true)==0x1100);put(0x1090,1);
    put(0x1080,0x1180);put(0x1180,4);put(0x1188,0x1120);assert(param()==0x1120);
    put(0x1190,0x1180);assert(!param());put(0x1190,0);put(0x1180,5);assert(!param());put(0x1180,4);
    put(0x1020,99);assert(!param());put(0x1020,3);put(0x1018,99);assert(!param());
    uint8_t data[40]{},kind{},affects{};double value{},number=.25;data[0]=3;data[16]=1;std::memcpy(data+8,&number,8);
    assert(e33_damage_evidence::values(data,kind,value,affects)&&kind==3&&value==.25&&affects==1);
    data[16]=2;assert(!e33_damage_evidence::values(data,kind,value,affects));data[16]=1;
    number=std::numeric_limits<double>::quiet_NaN();std::memcpy(data+8,&number,8);assert(!e33_damage_evidence::values(data,kind,value,affects));
    std::puts("Modifier frame identity, const-reference storage, bounded values and malformed inputs passed.");
}
