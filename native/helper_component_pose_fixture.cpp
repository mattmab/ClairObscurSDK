#define E33_RUNTIME_CINEMATIC_VERSION 192
#include "owned_battle_arena_channel.h"
#include <cassert>
#include <limits>
#include <initializer_list>
int main(){
    MeshPacket p{};p.operation=154;p.owner=5;
    auto bytes=reinterpret_cast<uint8_t*>(&p);bytes[24]=1;
    for(unsigned i=0;i<3;++i)p.inputs[i]={int32_t(i+1),int32_t(i+2),0x10000+uint64_t(i)*8};
    double before[]={0,0,0,1,0,0,0,0,750,749.9999821186066,749.9999821186066,0};
    double after[12]{};std::memcpy(after,before,sizeof(after));
    after[4]=-10186.739696838285;after[5]=27754.307872853868;after[6]=13586.391479276543;
    after[2]=std::sin(8.94778791834673*3.141592653589793/360.);
    after[3]=std::cos(8.94778791834673*3.141592653589793/360.);
    std::memcpy(bytes+2000,after,sizeof(after));
    assert(!e33_owned_arena::validate(p));assert(e33_component_pose::preserves_scale(before,after));
    assert(!e33_component_pose::same_scaled(before,after));
    double equivalent[12]{};std::memcpy(equivalent,after,sizeof(after));
    for(unsigned i=0;i<4;++i)equivalent[i]=-equivalent[i];
    assert(e33_component_pose::same_scaled(equivalent,after));
    equivalent[8]+=1;assert(!e33_component_pose::preserves_scale(equivalent,after));
    bytes[24]=0;assert(e33_owned_arena::validate(p)); // original arena rejects scaled pose
    for(unsigned selector: {2U,3U,255U}){bytes[24]=uint8_t(selector);assert(e33_owned_arena::validate(p));}
    bytes[24]=1;bytes[25]=1;assert(e33_owned_arena::validate(p));bytes[25]=0;
    for(double bad: {0.,-1.,1001.,std::numeric_limits<double>::infinity(),std::numeric_limits<double>::quiet_NaN()}){
        after[8]=bad;std::memcpy(bytes+2000,after,sizeof(after));assert(e33_owned_arena::validate(p));
    }
    after[8]=750;after[7]=1;std::memcpy(bytes+2000,after,sizeof(after));assert(e33_owned_arena::validate(p));
    after[7]=0;after[4]=100001;std::memcpy(bytes+2000,after,sizeof(after));assert(e33_owned_arena::validate(p));
}
