#pragma once
#include "story_inworld_packet.h"
namespace e33_story_ambient_overlay {
constexpr uint32_t operation=239,rejected=3970,uncertain=3971,pending=3972;
#pragma pack(push,1)
struct Packet {
 uint32_t version=3,op=operation,error=0,state=0;uint64_t owner=0;
 CallIdentity asset{},gi{},world{};uint64_t asset_lease=0,gi_lease=0,world_lease=0;
 uint32_t guid[4]{},mode=0,count=0,used_units=0,expected_count=0;
 CallIdentity system{},query{};
 e33_story_inworld::InputLine lines[16]{};uint16_t units[8192]{};uint8_t tail[1496]{};
};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984,"Ambient overlay packet");
inline bool valid(const Packet&p){
 if(p.version!=3||p.op!=operation||p.error||p.state||!p.owner||p.guid[0]!=0xe33c5701U||p.mode>2||
    !p.asset_lease||!p.gi_lease||p.world_lease||!e33_story_inworld::identity(p.asset)||!e33_story_inworld::identity(p.gi)||!e33_story_inworld::identity(p.world)||
    !e33_story_inworld::identity(p.system)||!e33_story_inworld::identity(p.query)||
    p.count>16||p.used_units>8192||p.expected_count>16||(p.mode?(p.count||p.used_units):(!p.count||!p.used_units)))return false;
 uint32_t end=0;
 for(unsigned i=0;i<16;++i){const auto&l=p.lines[i];
  if(i>=p.count){e33_story_inworld::InputLine zero{};if(std::memcmp(&l,&zero,sizeof(l)))return false;continue;}
  if((l.character!=0&&l.character!=1&&l.character!=8&&l.character!=9)||l.emotion||l.flags>3||l.reserved||
     !std::isfinite(l.delete_delay)||!std::isfinite(l.answer_delay)||l.delete_delay<0||l.delete_delay>120||l.answer_delay<0||l.answer_delay>120||
     l.text_start!=end||l.text_count>p.used_units-end||!valid_text_units(p.units+end,l.text_count))return false;
  for(const auto&id:{l.wave,l.sound,l.table})if(!e33_story_inworld::zero_identity(id)&&!e33_story_inworld::identity(id))return false;
  bool nul=false;for(char c:l.row){if(!c)nul=true;else if(nul||static_cast<unsigned char>(c)<32||static_cast<unsigned char>(c)>126)return false;}if(!nul)return false;
  end+=l.text_count;
 }
 if(end!=p.used_units)return false;
 for(unsigned i=end;i<8192;++i)if(p.units[i])return false;
 for(auto c:p.tail)if(c)return false;return true;
}
}
