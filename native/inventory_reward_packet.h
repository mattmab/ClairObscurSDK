#pragma once
#include "story_item_definitions_packet.h"
namespace e33_inventory_reward {
constexpr uint32_t operation=253,rejected=4230,uncertain=4231;
#pragma pack(push,1)
struct Packet {uint32_t version=3,op=operation,error=0,state=0;uint64_t owner=0;CallIdentity gi{},manager{},function{};uint64_t leases[3]{};uint32_t guid[4]{},outcome=0,mode=0;char item[96]{},character[96]{},quest[96]{},objective[96]{};uint8_t tail[20480]{};};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984,"Inventory reward packet");
inline bool valid(const Packet&p){
 if(p.version!=3||p.op!=operation||p.error||p.state||!p.owner||p.outcome||p.mode>2||p.guid[0]!=0xe33c5701U)return false;
 const CallIdentity ids[]={p.gi,p.manager,p.function};
 for(unsigned i=0;i<3;++i)if(!e33_story_inworld::identity(ids[i])||!p.leases[i])return false;
 for(auto v:p.tail)if(v)return false;
 if(!e33_story_items::ascii(p.item,96))return false;
 const char*names[]={p.character,p.quest,p.objective};
 for(unsigned i=0;i<3;++i){
  const bool required=p.mode==2?i==0:p.mode==0?i>0:false;
  if(required){if(!e33_story_items::ascii(names[i],96))return false;}
  else for(unsigned j=0;j<96;++j)if(names[i][j])return false;
 }
 return true;
}
}
