#pragma once
#include "invocation_protocol.h"
#include <cmath>
#include <cstring>
namespace e33_aim_region {
constexpr uint32_t operation=228, rejected=3800, unavailable=3801;
#pragma pack(push,1)
struct Packet {
    uint32_t version=3,op=operation,error=0,state=0;uint64_t owner=0;
    CallIdentity manager{};uint64_t token=0;CallIdentity source{};
    // System CDO, camera location/rotation, LineTraceSingle, BreakHitResult,
    // and the exact generated free-aim aim_point-part class.
    CallIdentity definitions[7]{};
    uint8_t reserved[80]{};
    uint32_t hit=0,body_part=0;
    CallIdentity actor{},component{},part{};
    double multiplier=0,base_damage=0;
    uint8_t tail[20656]{};
};
#pragma pack(pop)
static_assert(offsetof(Packet,hit)==256,"aim region output offset");
static_assert(sizeof(Packet)==20984,"aim region packet");
inline bool identity(const CallIdentity& v){return v.index>=0&&v.serial>=0&&v.address>=0x10000&&!(v.address&7);}
inline bool valid(const Packet& p){
    if(p.version!=3||p.op!=operation||p.error||p.state||!p.owner||!p.token||
       !identity(p.manager)||!identity(p.source)||p.hit||p.body_part||p.actor.address||p.actor.index||p.actor.serial||
       p.component.address||p.component.index||p.component.serial||p.part.address||p.part.index||p.part.serial||
       p.multiplier!=0||p.base_damage!=0)return false;
    for(const auto& id:p.definitions)if(!identity(id))return false;
    for(auto b:p.reserved)if(b)return false;
    for(auto b:p.tail)if(b)return false;
    return true;
}
inline bool ray(const double* position,const double* rotation,double* start,double* end){
    for(unsigned i=0;i<3;++i)if(!std::isfinite(position[i])||!std::isfinite(rotation[i])||std::abs(position[i])>1.e8)return false;
    constexpr double radians=3.14159265358979323846/180.;
    const double pitch=rotation[0]*radians,yaw=rotation[1]*radians;
    const double forward[]={std::cos(pitch)*std::cos(yaw),std::cos(pitch)*std::sin(yaw),std::sin(pitch)};
    for(unsigned i=0;i<3;++i){start[i]=position[i]+100.*forward[i];end[i]=position[i]+15000.*forward[i];}
    return true;
}
inline bool toward(const double* position,const double* aim_point,double* start,double* end){
    double distance2=0.;
    for(unsigned i=0;i<3;++i){
        if(!std::isfinite(position[i])||!std::isfinite(aim_point[i])||std::abs(position[i])>1.e8||std::abs(aim_point[i])>1.e8)return false;
        const double delta=aim_point[i]-position[i];distance2+=delta*delta;
    }
    const double distance=std::sqrt(distance2);
    if(distance<100.||distance>20000.)return false;
    for(unsigned i=0;i<3;++i){const double direction=(aim_point[i]-position[i])/distance;start[i]=position[i]+100.*direction;end[i]=aim_point[i]+5.*direction;}
    return true;
}
}

