#pragma once
#include <cstdint>
#include <cstring>
#include "story_item_definitions_packet.h"
namespace e33_encounter_action {
#pragma pack(push,1)
struct Profile {uint32_t flags=0;int32_t level_offset=0;uint32_t party_count=0,formations[6]{};char table_package[256]{},table_asset[96]{},encounter[96]{},music_package[256]{},music_asset[96]{},characters[6][96]{};};
#pragma pack(pop)
static_assert(sizeof(Profile)==1412);
inline bool path(const char*package,const char*asset){
 if(!e33_story_items::ascii(package,256,true)||std::strncmp(package,"/Game/",6)||!e33_story_items::ascii(asset,96))return false;
 const auto end=std::strrchr(package,'/');return end&&!std::strcmp(end+1,asset);
}
inline bool valid(const Profile&p){
 if(p.flags>15||p.level_offset< -99||p.level_offset>999||p.party_count>6||!path(p.table_package,p.table_asset)||!path(p.music_package,p.music_asset)||!e33_story_items::ascii(p.encounter,96))return false;
 for(unsigned i=0;i<6;++i){if(i<p.party_count){
   if(!e33_story_items::ascii(p.characters[i],96)||p.formations[i]>2)return false;
   for(unsigned j=0;j<i;++j)if(!std::strcmp(p.characters[i],p.characters[j]))return false;
  }else{if(p.formations[i])return false;for(auto c:p.characters[i])if(c)return false;}
 }return true;
}
inline void authored_values(uint8_t*frame,uint64_t table,uint64_t encounter,uint8_t*party,const uint8_t*music,const Profile&p){
 std::memcpy(frame,&table,8);std::memcpy(frame+8,&encounter,8);
 frame[97]=uint8_t(p.flags&1);frame[98]=uint8_t((p.flags>>1)&1);frame[192]=uint8_t((p.flags>>2)&1);frame[216]=uint8_t((p.flags>>3)&1);
 std::memcpy(frame+196,&p.level_offset,4);
 const uint64_t ptr=p.party_count?reinterpret_cast<uint64_t>(party):0;const int32_t count=int32_t(p.party_count);
 std::memcpy(frame+200,&ptr,8);std::memcpy(frame+208,&count,4);std::memcpy(frame+212,&count,4);
 std::memcpy(frame+104,music,40);
}
}
