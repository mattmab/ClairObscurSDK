#include "inventory_reward_packet.h"
#include "story_enemy_loot_packet.h"
#include <cassert>
#include <cstdio>
#include <cstddef>
template<size_t N>void set(char(&target)[N],const char*value){const size_t size=std::strlen(value);assert(size<N);std::memset(target,0,N);std::memcpy(target,value,size);}
e33_inventory_reward::Packet request(unsigned mode){
 e33_inventory_reward::Packet p;p.owner=1;p.mode=mode;
 p.gi={1,2,0x10000};p.manager={2,2,0x20000};p.function={3,2,0x30000};
 p.leases[0]=1;p.leases[1]=2;p.leases[2]=3;p.guid[0]=0xe33c5701U;
 set(p.item,"TestReward");
 if(mode==0){set(p.quest,"TestQuest");set(p.objective,"TestObjective");}
 if(mode==2)set(p.character,"TestGuardian");
 return p;
}
int main(){
 static_assert(offsetof(e33_inventory_reward::Packet,item)==120);
 for(unsigned mode:{0U,1U,2U}){
  auto p=request(mode);assert(e33_inventory_reward::valid(p));
  set(p.item,"AnotherReward");assert(e33_inventory_reward::valid(p));
  p.item[0]='/';assert(!e33_inventory_reward::valid(p));
  p=request(mode);p.tail[0]=1;assert(!e33_inventory_reward::valid(p));
  p=request(mode);p.leases[1]=0;assert(!e33_inventory_reward::valid(p));
  p=request(mode);p.guid[0]=0;assert(!e33_inventory_reward::valid(p));
  p=request(mode);p.mode=3;assert(!e33_inventory_reward::valid(p));
 }
 auto p=request(0);std::memset(p.objective,0,96);assert(!e33_inventory_reward::valid(p));
 p=request(1);set(p.character,"UnexpectedCharacter");assert(!e33_inventory_reward::valid(p));
 p=request(2);set(p.quest,"UnexpectedQuest");assert(!e33_inventory_reward::valid(p));
 p=request(2);std::memset(p.character,0,96);assert(!e33_inventory_reward::valid(p));
 e33_story_enemy_loot::Packet loot;loot.op=e33_story_enemy_loot::operation;loot.owner=1;loot.count=1;
 loot.target={1,2,0x10000};loot.source={2,2,0x20000};loot.map_class={3,2,0x30000};loot.map_add={4,2,0x40000};
 for(unsigned i=0;i<4;++i)loot.leases[i]=i+1;
 set(loot.source_package,"/Game/SDK/Example/Enemies");set(loot.source_asset,"Enemies");set(loot.names[0],"TestEnemy");
 CallIdentity gi{5,2,0x50000};uint64_t lease=5;uint32_t guid[4]={0xe33c5701U,2,3,4};
 auto raw=reinterpret_cast<uint8_t*>(&loot);std::memcpy(raw+2024,&gi,16);std::memcpy(raw+2040,&lease,8);std::memcpy(raw+2048,guid,16);std::memcpy(raw+2064,"TestReward",11);
 assert(e33_story_enemy_loot::valid(loot));set(loot.names[0],"AnotherEnemy");assert(e33_story_enemy_loot::valid(loot));
 raw[2160]=1;assert(!e33_story_enemy_loot::valid(loot));raw[2160]=0;std::memset(raw+2064,0,96);assert(!e33_story_enemy_loot::valid(loot));
 std::puts("Generic reward modes, enemy IDs, ownership and padding checks passed");
}
