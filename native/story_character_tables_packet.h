#pragma once
#include "story_item_definitions_packet.h"
namespace e33_story_character_tables {
constexpr uint32_t operation=255,rejected=4250,uncertain=4251;
using Packet=e33_story_items::Packet;
inline int profile(const Packet&p){
 const char* names[]={"DT_jRPG_CharacterDefinitions","DT_jRPG_CharacterSaveStates","DT_jRPG_WorldCharacters","DT_WeaponDefinitions"};
 for(int i=0;i<4;++i)if(!std::strcmp(p.source_asset,names[i]))return i;
 return -1;
}
inline const char* weapon_template(const Packet&p){return reinterpret_cast<const char*>(&p)+2064;}
inline bool package_matches(const Packet&p){
 const auto kind=profile(p);
 if(kind==3)return !std::strcmp(p.source_package,"/Game/Gameplay/Pictos/Gear/Weapons/DT_WeaponDefinitions");
 if(kind<0||std::strncmp(p.source_package,"/Game/SDK/",10))return false;
 const auto slash=std::strrchr(p.source_package,'/');return slash&&!std::strcmp(slash+1,p.source_asset);
}
inline bool valid(const Packet&p){
 if(!e33_story_items::ascii(p.source_asset,96)||!e33_story_items::ascii(p.source_package,256,true))return false;
 auto copy=p;copy.op=e33_story_items::operation;
 const auto bytes=reinterpret_cast<const uint8_t*>(&p);CallIdentity gi{};uint64_t lease=0;uint32_t guid=0;
 std::memcpy(&gi,bytes+2024,16);std::memcpy(&lease,bytes+2040,8);std::memcpy(&guid,bytes+2048,4);
 std::memset(reinterpret_cast<uint8_t*>(&copy)+2024,0,136);
 if(profile(p)==3){std::memset(copy.source_package,0,sizeof(copy.source_package));std::memcpy(copy.source_package,"/Game/SDK/WeaponTemplate",24);}
 if(p.op!=operation||!e33_story_items::valid(copy)||p.count!=1||!e33_story_inworld::identity(gi)||!lease||guid!=0xe33c5701U)return false;
 // Validate bounded source strings before any string comparison on this input.
 if(!e33_story_items::ascii(p.source_package,256,true)||!package_matches(p))return false;
 const char*name=weapon_template(p);
 if(profile(p)==3)return e33_story_items::ascii(name,96)&&std::strcmp(name,p.names[0]);
 for(unsigned i=0;i<96;++i)if(name[i])return false;return true;
}
}

