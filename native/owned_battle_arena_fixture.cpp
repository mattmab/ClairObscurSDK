#include "owned_battle_arena_channel.h"
#include <cassert>
#include <cstdio>
#include <limits>
int main(){
    MeshPacket p{};p.operation=151;p.owner=9;
    for(unsigned i=0;i<13;++i)p.inputs[i]={int32_t(i+1),int32_t(i+2),0x10000+uint64_t(i)*8};
    double pose[12]={0,0,0,1,1,2,3,0,1,1,1,0};
    std::memcpy(reinterpret_cast<uint8_t*>(&p)+2000,pose,sizeof(pose));
    assert(!e33_owned_arena::validate(p));
    auto bad=p;bad.vertex_count=1;assert(e33_owned_arena::validate(bad));
    bad=p;bad.operation=120;assert(e33_owned_arena::validate(bad));
    bad=p;bad.inputs[0].address++;assert(e33_owned_arena::validate(bad));
    bad=p;bad.inputs[12].serial=-1;assert(e33_owned_arena::validate(bad));
    bad=p;reinterpret_cast<uint8_t*>(&bad)[2096]=1;assert(e33_owned_arena::validate(bad));
    bad={};bad.operation=152;bad.owner=9;assert(!e33_owned_arena::validate(bad));
    bad.operation=153;assert(!e33_owned_arena::validate(bad));
    bad.actor={1,2,0x30000};assert(e33_owned_arena::validate(bad));
    MeshPacket change{};change.operation=154;change.owner=9;
    for(unsigned i=0;i<3;++i)change.inputs[i]=p.inputs[i];
    std::memcpy(reinterpret_cast<uint8_t*>(&change)+2000,pose,sizeof(pose));
    assert(!e33_owned_arena::validate(change));
    bad=change;bad.inputs[3]=p.inputs[3];assert(e33_owned_arena::validate(bad));
    bad=change;bad.inputs[0].address++;assert(e33_owned_arena::validate(bad));
    bad=change;reinterpret_cast<uint8_t*>(&bad)[4096]=1;assert(e33_owned_arena::validate(bad));
    double other[12];std::memcpy(other,pose,sizeof(pose));
    for(unsigned i=0;i<4;++i)other[i]=-other[i];
    assert(e33_component_pose::same(pose,other));
    other[4]+=.1;assert(!e33_component_pose::same(pose,other));
    other[8]=2;assert(!e33_component_pose::rigid(other));
    std::memcpy(other,pose,sizeof(pose));other[0]=std::numeric_limits<double>::quiet_NaN();
    assert(!e33_component_pose::rigid(other));
    std::memcpy(reinterpret_cast<uint8_t*>(&change)+2000,other,sizeof(other));
    assert(e33_owned_arena::validate(change));
    MeshPacket grounding{};grounding.operation=155;grounding.owner=9;
    for(unsigned i=0;i<9;++i)grounding.inputs[i]=p.inputs[i];
    assert(!e33_owned_arena::validate(grounding));
    bad=grounding;reinterpret_cast<uint8_t*>(&bad)[24]=1;assert(!e33_owned_arena::validate(bad));
    reinterpret_cast<uint8_t*>(&bad)[24]=2;assert(e33_owned_arena::validate(bad));
    reinterpret_cast<uint8_t*>(&bad)[24]=3;assert(!e33_owned_arena::validate(bad));
    reinterpret_cast<uint8_t*>(&bad)[24]=4;assert(e33_owned_arena::validate(bad));
    reinterpret_cast<uint8_t*>(&bad)[24]=5;assert(e33_owned_arena::validate(bad));
    reinterpret_cast<uint8_t*>(&bad)[24]=6;assert(e33_owned_arena::validate(bad));
    reinterpret_cast<uint8_t*>(&bad)[24]=7;assert(!e33_owned_arena::validate(bad));
    bad=grounding;reinterpret_cast<uint8_t*>(&bad)[25]=1;assert(e33_owned_arena::validate(bad));
    bad=grounding;bad.inputs[9]=p.inputs[9];assert(e33_owned_arena::validate(bad));
    bad=grounding;bad.inputs[8].address++;assert(e33_owned_arena::validate(bad));
    bad=grounding;reinterpret_cast<uint8_t*>(&bad)[2000]=1;assert(e33_owned_arena::validate(bad));
    MeshPacket helper{};helper.operation=156;helper.owner=9;
    for(unsigned i=0;i<4;++i)helper.inputs[i]=p.inputs[i];
    std::memcpy(reinterpret_cast<uint8_t*>(&helper)+2000,pose,sizeof(pose));
    assert(!e33_owned_arena::validate(helper));
    bad=helper;bad.inputs[4]=p.inputs[4];assert(e33_owned_arena::validate(bad));
    bad=helper;bad.inputs[0].address++;assert(e33_owned_arena::validate(bad));
    bad=helper;reinterpret_cast<uint8_t*>(&bad)[4096]=1;assert(e33_owned_arena::validate(bad));
    std::puts("Owned arena wire profiles passed; legacy enemy operations are not arena operations");
}
