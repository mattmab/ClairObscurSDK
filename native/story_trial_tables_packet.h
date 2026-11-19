#pragma once
#include "story_item_definitions_packet.h"
namespace e33_story_trial_tables {
constexpr uint32_t operation=254,rejected=4240,uncertain=4241,busy=4242;
using Packet=e33_story_items::Packet;
inline uint32_t kind(const Packet&p){uint32_t value=0;std::memcpy(&value,reinterpret_cast<const uint8_t*>(&p)+2064,4);return value;}
inline const char* reward(const Packet&p){return reinterpret_cast<const char*>(&p)+2068;}
inline bool valid(const Packet&p){
 auto copy=p;copy.op=e33_story_items::operation;
 const auto bytes=reinterpret_cast<const uint8_t*>(&p);CallIdentity gi{};uint64_t lease=0;uint32_t guid=0;
 std::memcpy(&gi,bytes+2024,16);std::memcpy(&lease,bytes+2040,8);std::memcpy(&guid,bytes+2048,4);
 std::memset(reinterpret_cast<uint8_t*>(&copy)+2024,0,140);
 if(p.op!=operation||!e33_story_items::valid(copy)||p.count!=1||kind(p)>1||!e33_story_inworld::identity(gi)||!lease||guid!=0xe33c5701U)return false;
 const auto slash=std::strrchr(p.source_package,'/');if(!slash||std::strcmp(slash+1,p.source_asset))return false;
 const auto name=reward(p);if(name[0])return e33_story_items::ascii(name,96);
 for(unsigned i=0;i<96;++i)if(name[i])return false;return true;
}
}
