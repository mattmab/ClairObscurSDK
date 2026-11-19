#include "story_character_tables_packet.h"
#include <cassert>
#include <cstdio>
using namespace e33_story_character_tables;
template<size_t N>void name(char(&dest)[N],const char*value){const size_t length=std::strlen(value);assert(length<N);std::memcpy(dest,value,length+1);}
static Packet request(bool weapon){
 Packet p;p.op=operation;p.owner=1;p.count=1;
 p.target={1,2,0x10000};p.source={2,2,0x20000};p.map_class={3,2,0x30000};p.map_add={4,2,0x40000};
 for(unsigned i=0;i<4;++i)p.leases[i]=i+1;
 name(p.source_asset,weapon?"DT_WeaponDefinitions":"DT_jRPG_CharacterDefinitions");
 name(p.source_package,weapon?"/Game/Gameplay/Pictos/Gear/Weapons/DT_WeaponDefinitions":"/Game/SDK/Example/DT_jRPG_CharacterDefinitions");
 name(p.names[0],weapon?"ExampleWand":"TestScholar");
 CallIdentity gi{5,2,0x50000};uint64_t lease=5;uint32_t guid[4]={0xe33c5701U,2,3,4};
 auto raw=reinterpret_cast<uint8_t*>(&p);std::memcpy(raw+2024,&gi,16);std::memcpy(raw+2040,&lease,8);std::memcpy(raw+2048,guid,16);
 if(weapon)std::memcpy(raw+2064,"ExampleSword",13);
 return p;
}
int main(){
 for(bool weapon:{false,true}){
  auto p=request(weapon);assert(e33_story_character_tables::valid(p));
  name(p.names[0],"TestGuardian");assert(e33_story_character_tables::valid(p));
  p.names[0][0]='/';assert(!e33_story_character_tables::valid(p));
  p=request(weapon);p.tail[136]=1;assert(!e33_story_character_tables::valid(p));
  p=request(weapon);p.leases[0]=0;assert(!e33_story_character_tables::valid(p));
  p=request(weapon);std::memset(p.source_asset,'X',96);assert(!e33_story_character_tables::valid(p));
 }
 auto p=request(false);p.tail[40]='A';assert(!e33_story_character_tables::valid(p));
 p=request(true);std::memset(p.tail+40,0,96);assert(!e33_story_character_tables::valid(p));
 p=request(true);std::memcpy(p.tail+40,p.names[0],96);assert(!e33_story_character_tables::valid(p));
 p=request(false);name(p.source_package,"/Game/SDK/Example/OtherTable");assert(!e33_story_character_tables::valid(p));
 std::puts("Generic character table profiles, template and save identity checks passed");
}
