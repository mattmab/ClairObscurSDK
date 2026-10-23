#pragma once
#include "mesh_protocol.h"
#include <cmath>
#include <cstring>
#include "component_pose_policy.h"
namespace e33_owned_arena {
constexpr uint32_t prepare=151,retire=152,status=153;
constexpr uint32_t component_pose=154;
constexpr uint32_t ground=155;
constexpr uint32_t qualify_helper=156;
inline uint32_t validate(const MeshPacket& packet){
    if(packet.version!=3||packet.error||packet.state||!packet.owner||
       (packet.operation!=prepare&&packet.operation!=retire&&packet.operation!=status&&packet.operation!=component_pose&&packet.operation!=ground&&packet.operation!=qualify_helper))return 3600;
    const auto* bytes=reinterpret_cast<const uint8_t*>(&packet);
    const bool spawn=packet.operation==prepare;
    const bool pose_change=packet.operation==component_pose;
    bool helper_pose=false;
#if E33_RUNTIME_CINEMATIC_VERSION>=192
    helper_pose=pose_change&&bytes[24]==1;
#endif
    const bool grounding=packet.operation==ground;
    const bool helper=packet.operation==qualify_helper;
    for(size_t i=24;i<sizeof(packet);++i)
        if(!((spawn&&i>=88&&i<296)||(pose_change&&i>=88&&i<136)||(helper_pose&&i==24)||(grounding&&i>=88&&i<232)||(grounding&&i==24)||(helper&&i>=88&&i<152)||((spawn||pose_change||helper)&&i>=2000&&i<2096))&&bytes[i])return 3600;
    if(helper){
        for(unsigned i=0;i<4;++i){CallIdentity id{};std::memcpy(&id,bytes+88+i*16,16);
            if(id.index<0||id.serial<0||id.address<0x10000||id.address>0x7fffffffffffULL||(id.address&7))return 3600;}
        double pose[12]{};std::memcpy(pose,bytes+2000,sizeof(pose));
        if(!e33_component_pose::rigid(pose)||std::abs(pose[0])>1.e-6||std::abs(pose[1])>1.e-6)return 3600;
    }
    if(grounding){
        if(bytes[24]!=0&&bytes[24]!=1&&bytes[24]!=3&&bytes[24]!=7)return 3600; // Advisory requires both screening and diagnostics.
        for(unsigned i=0;i<9;++i){CallIdentity id{};std::memcpy(&id,bytes+88+i*16,16);
            if(id.index<0||id.serial<0||id.address<0x10000||id.address>0x7fffffffffffULL||(id.address&7))return 3600;}
    }
    if(pose_change){
        for(unsigned i=0;i<3;++i){
            CallIdentity id{};std::memcpy(&id,bytes+88+i*16,16);
            if(id.index<0||id.serial<0||id.address<0x10000||id.address>0x7fffffffffffULL||(id.address&7))return 3600;
        }
        double pose[12]{};std::memcpy(pose,bytes+2000,sizeof(pose));
        if(!(helper_pose?e33_component_pose::scaled(pose):e33_component_pose::rigid(pose)))return 3600;
    }
    if(spawn){
        for(unsigned i=0;i<13;++i){
            CallIdentity id{};std::memcpy(&id,bytes+88+i*16,16);
            if(id.index<0||id.serial<0||id.address<0x10000||id.address>0x7fffffffffffULL||(id.address&7))return 3600;
        }
        double pose[12]{};std::memcpy(pose,bytes+2000,sizeof(pose));double norm=0;
        for(double v:pose)if(!std::isfinite(v)||std::abs(v)>1.e7)return 3600;
        for(unsigned i=0;i<4;++i)norm+=pose[i]*pose[i];
        if(norm<.999||norm>1.001||pose[7]||pose[11]||pose[8]!=1||pose[9]!=1||pose[10]!=1)return 3600;
    }
    return 0;
}
}
