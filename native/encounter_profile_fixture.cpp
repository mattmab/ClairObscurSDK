#include "encounter_action_profile.h"
#include "story_trial_tables_packet.h"
#include <cassert>
#include <cstddef>
#include <cstdio>
template<size_t N>void name(char(&target)[N],const char*text){const size_t size=std::strlen(text);assert(size<N);std::memset(target,0,N);std::memcpy(target,text,size);}
e33_encounter_action::Profile request(unsigned members){
 e33_encounter_action::Profile p;p.flags=5;p.level_offset=-3;p.party_count=members;
 name(p.table_package,"/Game/SDK/Sample/Encounters");name(p.table_asset,"Encounters");name(p.encounter,"SampleEncounter");
 name(p.music_package,"/Game/Audio/SampleTheme");name(p.music_asset,"SampleTheme");
 const char*characters[]={"First","Second","Third","Fourth","Fifth","Sixth"};
 for(unsigned i=0;i<members;++i){name(p.characters[i],characters[i]);p.formations[i]=i%3;}
 return p;
}
int main(){
 static_assert(offsetof(e33_encounter_action::Profile,table_package)==36);
 static_assert(offsetof(e33_encounter_action::Profile,music_package)==484);
 static_assert(offsetof(e33_encounter_action::Profile,characters)==836);
 for(unsigned count:{0U,2U,6U}){
  auto p=request(count);assert(e33_encounter_action::valid(p));
  p.flags=15;p.level_offset=12;assert(e33_encounter_action::valid(p));
  p.party_count=7;assert(!e33_encounter_action::valid(p));
 }
 auto p=request(2);name(p.characters[1],"First");assert(!e33_encounter_action::valid(p));
 p=request(2);p.formations[1]=3;assert(!e33_encounter_action::valid(p));
 p=request(0);p.characters[0][0]='X';assert(!e33_encounter_action::valid(p));
 p=request(1);p.music_package[255]='X';assert(!e33_encounter_action::valid(p));
 p=request(1);p.level_offset=-100;assert(!e33_encounter_action::valid(p));
 p=request(1);name(p.table_asset,"Other");assert(!e33_encounter_action::valid(p));
 for(unsigned kind:{0U,1U}){
  e33_story_trial_tables::Packet row;row.op=e33_story_trial_tables::operation;row.owner=1;row.count=1;
  row.target={1,2,0x10000};row.source={2,2,0x20000};row.map_class={3,2,0x30000};row.map_add={4,2,0x40000};for(unsigned i=0;i<4;++i)row.leases[i]=i+1;
  name(row.source_package,"/Game/SDK/Sample/Rows");name(row.source_asset,"Rows");name(row.names[0],"SampleRow");
  CallIdentity gi{5,2,0x50000};uint64_t lease=5;uint32_t guid[4]={0xe33c5701U,2,3,4};auto raw=reinterpret_cast<uint8_t*>(&row);
  std::memcpy(raw+2024,&gi,16);std::memcpy(raw+2040,&lease,8);std::memcpy(raw+2048,guid,16);std::memcpy(raw+2064,&kind,4);
  assert(e33_story_trial_tables::valid(row));std::memcpy(raw+2068,"SampleReward",13);assert(e33_story_trial_tables::valid(row));
  name(row.names[0],"AnotherRow");assert(e33_story_trial_tables::valid(row));
  raw[2164]=1;assert(!e33_story_trial_tables::valid(row));raw[2164]=0;raw[2064]=2;assert(!e33_story_trial_tables::valid(row));
 }
 std::puts("Generic encounter profiles, roster sizes, table kinds and padding checks passed");
}
