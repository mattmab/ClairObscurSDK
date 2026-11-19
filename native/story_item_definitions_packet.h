#pragma once
#include "story_inworld_packet.h"
namespace e33_story_items {
constexpr uint32_t operation=241,rejected=3990,uncertain=3991;
#pragma pack(push,1)
struct Packet {
 uint32_t version=3,op=operation,error=0,state=0;uint64_t owner=0;
 CallIdentity target{},source{},map_class{},map_add{};uint64_t leases[4]{};
 uint32_t mode=0,count=0,old_rows=0,new_rows=0;
 char source_package[256]{},source_asset[96]{},names[16][96]{};uint8_t tail[18960]{};
};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984,"Story item definition packet");
inline bool ascii(const char*value,unsigned capacity,bool path=false){
 bool nul=false;unsigned n=0;for(unsigned i=0;i<capacity;++i){const auto c=value[i];if(!c)nul=true;else{
  if(nul||!(c=='_'||(path&&c=='/')||(c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')))return false;++n;}}
 return nul&&n;
}
inline bool valid(const Packet&p){
 if(p.version!=3||p.op!=operation||p.error||p.state||!p.owner||p.mode>2||!p.count||p.count>16||p.old_rows||p.new_rows||
    !e33_story_inworld::identity(p.target)||!e33_story_inworld::identity(p.source)||!e33_story_inworld::identity(p.map_class)||!e33_story_inworld::identity(p.map_add)||
    !ascii(p.source_package,256,true)||std::strncmp(p.source_package,"/Game/SDK/",10)||!ascii(p.source_asset,96))return false;
 for(auto lease:p.leases)if(!lease)return false;
 for(unsigned i=0;i<16;++i){if(i<p.count){if(!ascii(p.names[i],96))return false;}else for(auto c:p.names[i])if(c)return false;}
 for(auto c:p.tail)if(c)return false;return true;
}
}
