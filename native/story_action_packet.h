#pragma once
#include "story_inworld_packet.h"
namespace e33_story_action {
constexpr uint32_t operation=236,rejected=3940,overflow=3941;
#pragma pack(push,1)
struct Source {CallIdentity object{};uint64_t lease=0;};
struct Receipt {uint64_t sequence=0;uint32_t source=0,reserved=0;CallIdentity world{};};
struct Packet {
 uint32_t version=3,op=operation,error=0,state=0;uint64_t owner=0;
 CallIdentity function{},gi{};uint64_t function_lease=0,gi_lease=0;
 uint32_t guid[4]{},mode=0,count=0;Source sources[8]{};
 uint64_t after=0;uint32_t used=0,reserved=0;Receipt receipts[32]{};
 uint8_t tail[19656]{};
};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984,"Story action packet");
inline bool valid(const Packet&p){
 if(p.version!=3||p.op!=operation||p.error||p.state||!p.owner||p.mode>2||p.count<1||p.count>8||
    !e33_story_inworld::identity(p.function)||!e33_story_inworld::identity(p.gi)||!p.function_lease||!p.gi_lease||
    p.guid[0]!=0xe33c5701U||p.used||p.reserved)return false;
 for(unsigned i=0;i<8;++i){const auto&s=p.sources[i];if(i<p.count){
  if(!e33_story_inworld::identity(s.object)||!s.lease)return false;
  for(unsigned j=0;j<i;++j)if(s.object.address==p.sources[j].object.address)return false;
 }else if(s.object.address||s.object.index||s.object.serial||s.lease)return false;}
 for(const auto&r:p.receipts)if(r.sequence||r.source||r.reserved||r.world.address||r.world.index||r.world.serial)return false;
 for(auto c:p.tail)if(c)return false;
 return true;
}
}
