#pragma once
#include "story_inworld_packet.h"
namespace e33_story_continuation {
constexpr uint32_t operation=238,rejected=3960,uncertain=3961;
#pragma pack(push,1)
struct Packet {
 uint32_t version=3,op=operation,error=0,state=0;uint64_t owner=0;
 CallIdentity function{},gi{},source{};uint64_t function_lease=0,gi_lease=0,source_lease=0;
 uint32_t guid[4]{},mode=0,reserved=0;uint64_t sequence=0;
 CallIdentity system{},dialogue{},world{};int32_t choice=-1;uint32_t pending=0;
 uint8_t tail[20800]{};
};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984,"Continuation packet");
inline bool valid(const Packet&p){
 if(p.version!=3||p.op!=operation||p.error||p.state||!p.owner||p.guid[0]!=0xe33c5701U||p.mode>4||p.reserved||
    !p.function_lease||!p.gi_lease||!p.source_lease||!e33_story_inworld::identity(p.function)||!e33_story_inworld::identity(p.gi)||!e33_story_inworld::identity(p.source)||
    !e33_story_inworld::zero_identity(p.system)||!e33_story_inworld::zero_identity(p.dialogue)||!e33_story_inworld::zero_identity(p.world)||p.choice!=-1||p.pending)return false;
 for(auto c:p.tail)if(c)return false;return true;
}
}
