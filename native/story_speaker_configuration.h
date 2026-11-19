#pragma once
#include "invocation_protocol.h"
#include "owned_text_value.h"
namespace e33_story_speaker {
constexpr uint32_t operation=232,rejected=3890,uncertain=3891;
constexpr uint32_t capacity=512;
#pragma pack(push,1)
struct Packet {
 uint32_t version=3,op=operation,error=0,state=0;
 uint64_t owner=0,speaker_lease=0;
 CallIdentity npc{},speaker{},system_cdo{},setter{};
 uint32_t count=0;uint16_t text[capacity]{};uint8_t tail[19860]{};
};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984,"Story speaker packet");
inline bool identity(const CallIdentity& id){return id.index>=0&&id.serial>0&&id.address>=0x10000&&id.address<=0x7fffffffffffULL&&!(id.address&7);}
inline bool valid(const Packet& p){
 if(p.version!=3||p.op!=operation||p.error||p.state||!p.owner||!p.speaker_lease||
    !identity(p.npc)||!identity(p.speaker)||!identity(p.system_cdo)||!identity(p.setter)||
    p.count<2||p.count>capacity||!valid_text_units(p.text,p.count))return false;
 for(uint32_t i=p.count;i<capacity;++i)if(p.text[i])return false;
 for(auto v:p.tail)if(v)return false;
 return true;
}
}
