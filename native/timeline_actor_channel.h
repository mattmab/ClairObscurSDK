#pragma once
#include "mesh_protocol.h"
#include <cmath>
#include <cstring>
namespace e33_timeline_actor {
constexpr uint32_t construct=223,reveal=224,retire=225;
constexpr unsigned capacity=32;
class Slots {
    uint64_t tokens_[capacity]{};
public:
    int find(uint64_t token)const{
        if(token)for(unsigned i=0;i<capacity;++i)if(tokens_[i]==token)return static_cast<int>(i);
        return -1;
    }
    int reserve(uint64_t token){
        if(!token||find(token)>=0)return -1;
        for(unsigned i=0;i<capacity;++i)if(!tokens_[i]){tokens_[i]=token;return static_cast<int>(i);}
        return -1;
    }
    bool reserved(unsigned slot)const{return slot<capacity&&tokens_[slot]!=0;}
    bool retired(unsigned slot,uint32_t error,bool has_work){
        if(slot>=capacity||error||has_work)return false;
        tokens_[slot]=0;return true;
    }
};
inline uint32_t validate(const MeshPacket& p){
    if(p.version!=3||p.error||p.state||!p.owner||
       (p.operation!=construct&&p.operation!=reveal&&p.operation!=retire))return 3768;
    const auto* bytes=reinterpret_cast<const uint8_t*>(&p);
    const bool spawn=p.operation==construct;
    for(size_t i=24;i<sizeof(p);++i)
        if(!(spawn&&((i>=88&&i<296)||(i>=2000&&i<2096)))&&bytes[i])return 3768;
    if(spawn){
        for(unsigned i=0;i<13;++i){CallIdentity id{};std::memcpy(&id,bytes+88+i*16,16);
            if(id.index<0||id.serial<0||id.address<0x10000||id.address>0x7fffffffffffULL||(id.address&7))return 3768;}
        double pose[12]{};std::memcpy(pose,bytes+2000,sizeof(pose));double norm=0;
        for(auto value:pose)if(!std::isfinite(value)||std::abs(value)>1.e7)return 3768;
        for(unsigned i=0;i<4;++i)norm+=pose[i]*pose[i];
        if(norm<.999||norm>1.001||pose[7]||pose[11]||pose[8]!=1||pose[9]!=1||pose[10]!=1)return 3768;
    }
    return 0;
}
}
