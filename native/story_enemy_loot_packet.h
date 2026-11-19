#pragma once
#include "story_item_definitions_packet.h"
namespace e33_story_enemy_loot {
constexpr uint32_t operation=251,rejected=4210,uncertain=4211;
using Packet=e33_story_items::Packet;
inline bool valid(const Packet&p){
 auto copy=p;copy.op=e33_story_items::operation;
 CallIdentity gi{};uint64_t lease=0;uint32_t guid[4]{};const auto bytes=reinterpret_cast<const uint8_t*>(&p);
 std::memcpy(&gi,bytes+2024,16);std::memcpy(&lease,bytes+2040,8);std::memcpy(guid,bytes+2048,16);
 std::memset(reinterpret_cast<uint8_t*>(&copy)+2024,0,136);
 return p.op==operation&&e33_story_items::valid(copy)&&p.count==1&&e33_story_items::ascii(reinterpret_cast<const char*>(&p)+2064,96)&&
  e33_story_inworld::identity(gi)&&lease&&guid[0]==0xe33c5701U;
}
}
