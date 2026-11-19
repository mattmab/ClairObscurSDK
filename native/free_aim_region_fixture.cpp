#include "free_aim_region.h"
#include <cassert>
#include <limits>
int main(){
    using namespace e33_aim_region;
    Packet p{};p.owner=1;p.token=2;p.manager={3,4,0x10000};p.source={5,6,0x20000};
    for(unsigned i=0;i<7;++i)p.definitions[i]={int32_t(10+i),20,0x30000+uint64_t(i)*8};
    assert(valid(p));
    auto q=p;q.owner=0;assert(!valid(q));q=p;q.token=0;assert(!valid(q));
    q=p;q.reserved[79]=1;assert(!valid(q));q=p;q.tail[20655]=1;assert(!valid(q));
    q=p;q.definitions[6].address=0;assert(!valid(q));q=p;q.hit=1;assert(!valid(q));
    q=p;q.part.address=0x40000;assert(!valid(q));q=p;q.multiplier=2.;assert(!valid(q));
    double location[]={10,20,30},rotation[]={0,0,0},start[3]{},end[3]{};
    assert(ray(location,rotation,start,end));assert(start[0]==110&&start[1]==20&&end[0]==15010);
    rotation[0]=90;assert(ray(location,rotation,start,end));assert(std::abs(start[2]-130)<1.e-9);
    location[0]=std::numeric_limits<double>::quiet_NaN();assert(!ray(location,rotation,start,end));
    double origin[]={0,0,0},aim[]={0,500,0};
    assert(toward(origin,aim,start,end));assert(start[1]==100&&end[1]==505);
    aim[1]=0;assert(!toward(origin,aim,start,end));aim[1]=30000;assert(!toward(origin,aim,start,end));
}
