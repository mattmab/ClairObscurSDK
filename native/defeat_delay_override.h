#pragma once
#include "invocation_protocol.h"
#include <cstring>
namespace e33_defeat_delay {
constexpr uint32_t operation=227, rejected=3790, conflict=3791;
#pragma pack(push,1)
struct Packet {
    uint32_t version=3,op=operation,error=0,state=0;uint64_t owner=0;
    CallIdentity function{};uint64_t token=0;uint32_t mode=0;
    uint8_t tail[20932]{};
};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984,"defeat delay packet");
inline bool valid(const Packet& p){
    if(p.version!=3||p.op!=operation||p.error||p.state||!p.owner||!p.token||
       p.function.index<0||p.function.serial<=0||!p.function.address||(p.mode!=1&&p.mode!=2))return false;
    for(auto b:p.tail)if(b)return false;
    return true;
}
struct Frame {
    Packet held{};uint64_t storage=0;bool active=false;
    bool protects(uint64_t token)const{return active&&held.token==token;}
    template<class Ops> uint32_t close(Ops& ops){
        if(!active)return 0;
        uint64_t current=0;
        if(!ops.resolve(held,current)||current!=storage||ops.bits(storage)!=0)return conflict;
        ops.write(storage,0x41000000U);
        if(ops.bits(storage)!=0x41000000U)return conflict;
        active=false;storage=0;held={};return 0;
    }
    template<class Ops> void run(Packet& p,Ops& ops){
        if(!valid(p)){p.error=rejected;return;}
        if(active&&(p.owner!=held.owner||p.token!=held.token||std::memcmp(&p.function,&held.function,sizeof(CallIdentity)))){p.error=conflict;return;}
        if(p.mode==2){p.error=close(ops);p.state=p.error?2U:0U;return;}
        if(active){p.state=1;return;}
        uint64_t at=0;
        if(!ops.resolve(p,at)||ops.bits(at)!=0x41000000U){p.error=rejected;return;}
        held=p;storage=at;active=true; // Journal before the single fixed write.
        ops.write(at,0);
        if(ops.bits(at)!=0){p.error=conflict;p.state=2;return;}
        p.state=1;
    }
};
}
