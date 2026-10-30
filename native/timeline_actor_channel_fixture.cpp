#include "timeline_actor_channel.h"
#include <cassert>
#include <limits>
#include <initializer_list>
int main(){
    using namespace e33_timeline_actor;
    Slots slots;
    assert(slots.reserve(0)==-1&&slots.find(0)==-1);
    for(unsigned i=0;i<capacity;++i){assert(slots.reserve(i+1)==static_cast<int>(i));assert(slots.find(i+1)==static_cast<int>(i));}
    assert(slots.reserve(1)==-1&&slots.reserve(capacity+1)==-1);
    assert(!slots.retired(0,3772,false)&&!slots.retired(0,0,true));
    assert(slots.find(1)==0&&slots.reserve(capacity+1)==-1);
    assert(slots.retired(4,0,false)&&slots.find(5)==-1);
    assert(slots.reserve(1000)==4&&slots.find(1000)==4&&slots.find(1)==0);
    assert(!slots.retired(capacity,0,false));
    MeshPacket p{};p.operation=construct;p.owner=123;
    for(unsigned i=0;i<13;++i)p.inputs[i]={static_cast<int32_t>(i),1,0x10000+i*256};
    const double pose[]={0,0,0,1,100,200,300,0,1,1,1,0};
    std::memcpy(reinterpret_cast<uint8_t*>(&p)+2000,pose,sizeof(pose));
    assert(!validate(p));
    for(unsigned i:{24U,87U,296U,1999U,2096U,4096U,20983U}){
        auto bad=p;reinterpret_cast<uint8_t*>(&bad)[i]=1;assert(validate(bad));
    }
    auto bad=p;bad.inputs[0].serial=-1;assert(validate(bad));
    bad=p;bad.inputs[12].address++;assert(validate(bad));
    bad=p;reinterpret_cast<double*>(reinterpret_cast<uint8_t*>(&bad)+2000)[4]=std::numeric_limits<double>::infinity();assert(validate(bad));
    for(auto op:{reveal,retire}){
        MeshPacket empty{};empty.operation=op;empty.owner=123;assert(!validate(empty));
        empty.inputs[0]={1,1,0x10000};assert(validate(empty));
    }
    bad=p;bad.operation=120;assert(validate(bad));
    bad=p;bad.owner=0;assert(validate(bad));
    bad=p;bad.state=1;assert(validate(bad));
}
