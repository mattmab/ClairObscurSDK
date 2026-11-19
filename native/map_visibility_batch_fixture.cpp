#include "map_visibility_batch.h"
#include <array>
#include <cassert>
#include <iostream>
using namespace e33_map_visibility;
struct Fake {
    bool schema=true,hidden[capacity]{},collision[capacity]{},owned[capacity]{};
    uint32_t calls=0,hide_calls=0,fail_current_at=0,invalid=capacity,budget=capacity;
    bool reject_hide=false,lose_collision=false,ignore_hide=false;
    Fake(){std::fill(collision,collision+capacity,true);std::fill(owned,owned+capacity,true);}
    bool function(){return schema;}
    bool current(){return ++calls!=fail_current_at;}
    bool observe(uint32_t i,bool& value){value=hidden[i];return owned[i]&&collision[i]&&i!=invalid;}
    bool hide(uint32_t i){++hide_calls;if(reject_hide)return false;if(!ignore_hide)hidden[i]=true;if(lose_collision)collision[i]=false;return true;}
    bool budget_exhausted(){return hide_calls>=budget;}
};
template<class T> void put(std::array<uint8_t,packet_size>& p,size_t at,T value){std::memcpy(p.data()+at,&value,sizeof(value));}
int main(){
    std::array<uint8_t,packet_size> packet{};put<uint32_t>(packet,0,3);put(packet,4,operation);put<uint64_t>(packet,16,7);
    put(packet,88,Identity{1,2,0x10000});put<uint32_t>(packet,2000,2);
    put(packet,4096,Identity{2,3,0x20000});put(packet,4112,Identity{3,4,0x30000});assert(valid(packet.data(),packet.size()));
    for(size_t at:{size_t(8),size_t(24),size_t(104),size_t(2004),size_t(4128)}){auto bad=packet;bad[at]=1;assert(!valid(bad.data(),bad.size()));}
    {auto bad=packet;put(bad,4112,Identity{2,3,0x20000});assert(!valid(bad.data(),bad.size()));}
    {auto bad=packet;put<uint32_t>(bad,2000,33);assert(!valid(bad.data(),bad.size()));}
    {auto bad=packet;put(bad,88,Identity{1,0,0x10000});assert(!valid(bad.data(),bad.size()));}
    {Fake f;auto r=run(f,3);assert(!r.error&&r.completed==3&&!r.quarantine&&f.hide_calls==3);for(unsigned i=0;i<3;++i)assert(f.hidden[i]&&f.collision[i]);}
    {Fake f;f.schema=false;auto r=run(f,3);assert(r.error==rejected&&!r.completed&&!f.hide_calls);}
    {Fake f;f.owned[2]=false;auto r=run(f,3);assert(r.error==rejected&&!r.completed&&!f.hide_calls);}
    {Fake f;f.collision[2]=false;auto r=run(f,3);assert(r.error==rejected&&!r.quarantine&&!f.hide_calls);}
    {Fake f;f.fail_current_at=4;auto r=run(f,3);assert(r.error==rejected&&!r.quarantine&&!f.hide_calls);}
    {Fake f;f.fail_current_at=6;auto r=run(f,3);assert(r.error==uncertain&&r.completed==1&&r.quarantine&&f.hide_calls==1);}
    {Fake f;f.reject_hide=true;auto r=run(f,3);assert(r.error==uncertain&&!r.completed&&r.quarantine&&f.hide_calls==1);}
    {Fake f;f.lose_collision=true;auto r=run(f,3);assert(r.error==uncertain&&!r.completed&&r.quarantine);}
    {Fake f;f.ignore_hide=true;auto r=run(f,3);assert(r.error==uncertain&&!r.completed&&r.quarantine);}
    {Fake f;f.budget=1;auto r=run(f,3);assert(!r.error&&r.completed==1&&!r.quarantine&&f.hide_calls==1&&!f.hidden[1]);}
    {Fake f;std::fill(f.hidden,f.hidden+capacity,true);auto r=run(f,3);assert(!r.error&&r.completed==3&&!f.hide_calls);}
    std::cout<<"Owned map visibility batch checks passed\n";
}
