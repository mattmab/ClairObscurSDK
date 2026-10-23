#pragma once
#include "qa_encounter_protocol.h"
#include "numbered_field_name.h"
#include "picto_stat_remove.h"
// QA-only removal of this respawnable actor's temporary defeat record.
// The permanent battle/encounter history and every other enemy remain intact.
inline bool qa_history_view(uint64_t base,uint64_t map,uint64_t descriptor,uint64_t key,int& entry,uint64_t& fingerprint) {
 entry=-1;fingerprint=1469598103934665603ULL;
 if(local_read<uint8_t>(descriptor+0x98)&1)return false;
 const auto kp=local_read<uint64_t>(descriptor+0x70),vp=local_read<uint64_t>(descriptor+0x78);
 if(!kp||!vp||local_read<uint64_t>(kp+0x10)!=descriptor||local_read<uint64_t>(vp+0x10)!=descriptor ||
 !exact_name(base,local_read<uint64_t>(kp+8),"NameProperty") || !exact_name(base,local_read<uint64_t>(vp+8),"BoolProperty") ||
 local_read<int32_t>(kp+0x30)!=1||local_read<int32_t>(vp+0x30)!=1||local_read<int32_t>(kp+0x34)!=8||local_read<int32_t>(vp+0x34)!=1||
 local_read<int32_t>(kp+0x44)!=0||local_read<int32_t>(vp+0x44)!=8||local_read<uint32_t>(vp+0x70)!=0xff010001 ||
 local_read<int32_t>(descriptor+0x80)!=8||local_read<int32_t>(descriptor+0x84)!=12||local_read<int32_t>(descriptor+0x88)!=16||local_read<int32_t>(descriptor+0x8c)!=20)return false;
 const int count=local_read<int32_t>(map+8),cap=local_read<int32_t>(map+12),free=local_read<int32_t>(map+52),size=local_read<int32_t>(map+72);
 const auto data=local_read<uint64_t>(map),bh=local_read<uint64_t>(map+32),bits=bh?bh:map+16,hh=local_read<uint64_t>(map+64),buckets=hh?hh:map+56;
 if(count<0||count>cap||cap>4096||free<0||free>count||local_read<int32_t>(map+40)!=count||local_read<int32_t>(map+44)<count||local_read<int32_t>(map+44)>4096||(!bh&&count>128)||
 size<0||size>8192||(size&&(size&(size-1)))||(!hh&&size>2)||(count&&(!data||(data&3))))return false;
 bool seen[4096]{};int visited=0;
 for(int bucket=0;bucket<size;++bucket) {
  auto index=local_read<int32_t>(buckets+uint64_t(bucket)*4);
  for(int links=0;index!=-1;++links) {
   if(index<0||index>=count||links>=count||seen[index]||!(local_read<uint32_t>(bits+uint64_t(index/32)*4)&(1U<<(index%32))))return false;
   auto at=data+uint64_t(index)*20;
   if((local_read<uint32_t>(at+16)&uint32_t(size-1))!=uint32_t(bucket))return false;
   seen[index]=true;++visited;index=local_read<int32_t>(at+12);
  }
 }
 if(visited!=count-free)return false;
 for(int i=0;i<count;++i)if(seen[i]) {
  auto at=data+uint64_t(i)*20;auto name=local_read<uint64_t>(at);auto value=local_read<uint8_t>(at+8);
  if(value>1)return false;
  if(name==key){if(entry!=-1)return false;entry=i;continue;}
  fingerprint^=name;fingerprint*=1099511628211ULL;fingerprint^=value;fingerprint*=1099511628211ULL;
 }
 return true;
}
inline void qa_encounter_reset(uint64_t base,QAEncounterPacket& p) {
 if(p.version!=1||p.operation!=1||p.error||p.outcome||p.removed||p.reserved){p.error=1900;return;}
 const auto w=call_identity(base,p.world),e=call_identity(base,p.enemy),c=call_identity(base,p.component),gi=call_identity(base,p.gi),fn=call_identity(base,p.function);
 if(!w||!e||!c||!gi||!fn || !zone_named(base,w,"Map_BattleTesting","/Game/QA/Map_BattleTesting") ||
 !exact_name(base,local_read<uint64_t>(w+16)+24,"World") || zone_ref(base,w,"OwningGameInstance")!=gi ||
 !exact_field_name(base,e+24,"BP_jRPG_EnemyWorld_Gault_C",1) || local_read<uint64_t>(local_read<uint64_t>(e+32)+32)!=w ||
 !picto_class(base,e,"BP_jRPG_EnemyWorld_Gault_C","/Game/Characters/Enemies/YellowForest/Gault/BP_jRPG_EnemyWorld_Gault") ||
 local_read<uint64_t>(c+32)!=e || !exact_name(base,local_read<uint64_t>(c+16)+24,"BP_Enemy_SerializableComponent_C") ||
 !picto_class(base,gi,"BP_jRPG_GI_Custom_C","/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_GI_Custom")){p.error=1901;return;}
 const auto battle=picto_field(base,e,"IsInBattle","BoolProperty",2930,1),respawn=picto_field(base,e,"RespawnsOnRest","BoolProperty",2168,1),changing=picto_field(base,gi,"IsChangingMap","BoolProperty",464,1);
 if(!battle||!respawn||!changing||local_read<uint8_t>(battle)||!local_read<uint8_t>(respawn)||local_read<uint8_t>(changing)){p.error=1906;return;}
 const auto id=picto_field(base,c,"GlobalObjectID","NameProperty",160,8);
 if(!id||!exact_name(base,id,"ObjectID_Enemy_Map_BattleTesting_BP_jRPG_EnemyWorld_Gault_C_5545DCA04759C88FA9702F95F0EDE6A5") ||
 !exact_name(base,fn+24,"Map_Remove") || local_read<uint64_t>(fn+0xd8)!=base+0x34cc740 ||
 !zone_named(base,local_read<uint64_t>(fn+32),"BlueprintMapLibrary","/Script/Engine") || !picto_remove_code(base)){p.error=1902;return;}
 uint64_t desc=0;const auto map=picto_field(base,gi,"TransientBattledEnemies","MapProperty",1432,80,&desc);
 int entry=-1;uint64_t before=0;
 if(!map||!qa_history_view(base,map,desc,local_read<uint64_t>(id),entry,before)){p.error=1903;return;}
 if(entry<0){p.outcome=1;return;}
 alignas(8) uint8_t helper[56]{};const auto key=local_read<uint64_t>(desc+0x70),value=local_read<uint64_t>(desc+0x78);
 std::memcpy(helper,&key,8);std::memcpy(helper+8,&value,8);std::memcpy(helper+16,&map,8);std::memcpy(helper+24,reinterpret_cast<void*>(desc+0x80),24);helper[48]=local_read<uint8_t>(desc+0x98);
 struct Removal{void* helper;int32_t index,count;} removal{helper,entry,1};p.outcome=2;
 reinterpret_cast<void(__fastcall*)(void*,void*)>(base+0x1356870)(helper,&removal);
 uint64_t after=0;if(!qa_history_view(base,map,desc,local_read<uint64_t>(id),entry,after)||entry!=-1||after!=before){p.error=1904;return;}
 p.removed=1;p.outcome=1;
}
