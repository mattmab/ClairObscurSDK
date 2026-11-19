#pragma once
#include "invocation_protocol.h"
#include "dialogue_text_array_frame.h"
namespace e33_dialogue_text {
constexpr uint32_t operation=229,units_capacity=8192;
#pragma pack(push,1)
struct Packet {
    uint32_t version=3,op=operation,error=0,state=0;uint64_t owner=0;
    CallIdentity system{},dialogue{},function{},speaker{};
    uint64_t dialogue_lease=0;
    uint32_t mode=0,count=0,used_units=0,reserved=0;
    uint32_t starts[capacity]{},lengths[capacity]{};
    uint16_t units[units_capacity]{};
    uint8_t tail[4360]{};
};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984,"Native dialogue packet size");
inline bool valid_identity(const CallIdentity& id){
    return id.index>=0&&id.serial>=0&&id.address>=0x10000&&id.address<=0x7fffffffffffULL&&!(id.address&7);
}
inline bool valid_packet(const Packet& p){
    if(p.version!=3||p.op!=operation||p.error||p.state||!p.owner||!p.dialogue_lease||p.reserved||
       p.mode>2||p.count>capacity||p.used_units>units_capacity||
       (p.mode==2?(p.count||p.used_units):(!p.count||!p.used_units))||
       !valid_identity(p.system)||!valid_identity(p.dialogue)||!valid_identity(p.function))return false;
    if(p.mode==0){if(!valid_identity(p.speaker))return false;}
    else if(p.speaker.index||p.speaker.serial||p.speaker.address)return false;
    uint32_t end=0;
    for(uint32_t i=0;i<capacity;++i){
        if(i>=p.count){if(p.starts[i]||p.lengths[i])return false;continue;}
        if(p.starts[i]!=end||p.lengths[i]>p.used_units-end||!valid_text_units(p.units+end,p.lengths[i]))return false;
        end+=p.lengths[i];
    }
    if(end!=p.used_units)return false;
    for(uint32_t i=end;i<units_capacity;++i)if(p.units[i])return false;
    for(auto b:p.tail)if(b)return false;
    return true;
}
}
