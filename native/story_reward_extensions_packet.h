#pragma once
#include "story_item_definitions_packet.h"
namespace e33_story_rewards {
constexpr uint32_t operation=242,rejected=4000,uncertain=4001;
#pragma pack(push,1)
struct Packet {
 uint32_t version=3,op=operation,error=0,state=0;uint64_t owner=0;
 CallIdentity gi{},system{},function{},flower_class{},jules_class{};uint64_t leases[4]{};
 uint32_t guid[4]{};uint64_t definitions_owner=0;
 uint32_t mode=0,reserved[3]{};char origins[2][96]{},extras[2][2][96]{};
 uint64_t calls[2]{},grants[2]{};uint8_t tail[20200]{};
};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984,"Story reward extension packet");
inline bool valid(const Packet&p){
 if(p.version!=3||p.op!=operation||p.error||p.state||!p.owner||p.guid[0]!=0xe33c5701U||!p.definitions_owner||p.mode>2||
    !e33_story_inworld::identity(p.gi)||!e33_story_inworld::identity(p.system)||!e33_story_inworld::identity(p.function)||!e33_story_inworld::identity(p.flower_class)||!e33_story_inworld::identity(p.jules_class))return false;
 for(auto lease:p.leases)if(!lease)return false;
 for(auto value:p.reserved)if(value)return false;
 for(auto value:p.calls)if(value)return false;for(auto value:p.grants)if(value)return false;
 for(unsigned i=0;i<2;++i){if(!e33_story_items::ascii(p.origins[i],96))return false;
  for(unsigned j=0;j<2;++j){if(i==1&&j==1){for(auto c:p.extras[i][j])if(c)return false;}else if(!e33_story_items::ascii(p.extras[i][j],96))return false;}}
 for(auto c:p.tail)if(c)return false;return true;
}
}
