#pragma once
#include "story_inworld_packet.h"
namespace e33_story_rewrite {
constexpr uint32_t operation=237,rejected=3950,uncertain=3951;
constexpr unsigned capacity=8,profiles_capacity=8,units_capacity=8192;
#pragma pack(push,1)
struct Text {uint32_t before_start=0,before_count=0,after_start=0,after_count=0;};
struct Packet {
 uint32_t version=3,op=operation,error=0,state=0;uint64_t owner=0;
 CallIdentity function{},gi{},source{};uint64_t function_lease=0,gi_lease=0,source_lease=0;
 uint32_t guid[4]{},mode=0,count=0,profile=0,reserved=0;uint64_t hits[capacity]{};
 Text texts[capacity]{};uint16_t units[units_capacity]{};
 CallIdentity text_cdo{},text_query{};uint64_t text_cdo_lease=0,text_query_lease=0;
 CallIdentity sound{};uint64_t sound_lease=0;uint32_t sound_mask=0,sound_reserved=0;uint8_t tail[4200]{};
};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984,"Story rewrite packet");
inline bool valid(const Packet&p){
 if(p.version!=3||p.op!=operation||p.error||p.state||!p.owner||p.guid[0]!=0xe33c5701U||p.mode>2||p.profile>=profiles_capacity||
    p.reserved||!p.function_lease||!p.gi_lease||!p.source_lease||!e33_story_inworld::identity(p.function)||
    !e33_story_inworld::identity(p.gi)||!e33_story_inworld::identity(p.source)||!e33_story_inworld::identity(p.text_cdo)||!e33_story_inworld::identity(p.text_query)||
    !p.text_cdo_lease||!p.text_query_lease||
    (p.mode? p.count!=0 : (!p.count||p.count>capacity)))return false;
 uint32_t end=0;
 for(unsigned i=0;i<capacity;++i){
  if(p.hits[i])return false;
  const auto&t=p.texts[i];
  if(i>=p.count){Text zero{};if(std::memcmp(&t,&zero,sizeof(t)))return false;continue;}
  if(t.before_start!=end||t.before_count>units_capacity-end||!valid_text_units(p.units+end,t.before_count))return false;
  end+=t.before_count;
  if(t.after_start!=end||t.after_count>units_capacity-end||!valid_text_units(p.units+end,t.after_count))return false;
  end+=t.after_count;
 }
 for(unsigned i=end;i<units_capacity;++i)if(p.units[i])return false;
 if(p.sound_reserved||p.sound_mask>255)return false;
 if(p.sound_mask){if(!e33_story_inworld::identity(p.sound)||!p.sound_lease||(!p.mode&&(p.sound_mask>>p.count)))return false;}
 else if(p.sound.address||p.sound.index||p.sound.serial||p.sound_lease)return false;
 for(auto c:p.tail)if(c)return false;
 return true;
}
}
