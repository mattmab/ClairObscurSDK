#pragma once
#include "qa_encounter_protocol.h"
// SoftObjectProperty CopyValuesInternal is the engine assignment operator;
// it copies the FString subpath with engine allocation/ownership intact.
inline CallIdentity qa_mime_default{};
alignas(8) inline uint8_t qa_mime_original[40]{};
inline uint64_t qa_mime_descriptor=0;
inline bool qa_soft_copy_ready(uint64_t base) {
 return local_read<uint64_t>(base+0x6e128d8+0xf0)==base+0x1368190 &&
 local_read<uint8_t>(base+0x1368190)==0x45 && local_read<uint8_t>(base+0x1368191)==0x85 && local_read<uint8_t>(base+0x1368192)==0xc9;
}
inline uint64_t qa_battle_soft(uint64_t base,uint64_t object,const char* field,int offset,uint64_t& descriptor) {
 uint64_t outer=0;const auto storage=picto_field(base,object,field,"StructProperty",offset,344,&outer);
 const auto st=outer?local_read<uint64_t>(outer+0x70):0;
 if(!storage || !zone_named(base,st,"FBattleStartParams","/Game/Gameplay/Battle/FBattleStartParams") || local_read<uint32_t>(st+0x58)!=344)return 0;
 unsigned walked=0;
 for(auto f=local_read<uint64_t>(st+0x50);f && ++walked<64;f=local_read<uint64_t>(f+0x18)) {
  if(!exact_name(base,f+0x20,"BattleMapBPSoft_41_9D55F2484E1768C57CF31794DEDE717F"))continue;
  if(local_read<uint64_t>(f)!=base+0x6e128d8 || local_read<uint64_t>(f+0x10)!=(st|1) || local_read<uint32_t>(f+0x44)!=40 || local_read<uint32_t>(f+0x34)!=40 || local_read<uint32_t>(f+0x30)!=1)return 0;
  descriptor=f;return storage+40;
 }
 return 0;
}
inline void qa_soft_copy(uint64_t base,uint64_t descriptor,void* destination,const void* source) {
 reinterpret_cast<void(__fastcall*)(void*,void*,const void*,int)>(base+0x1368190)(reinterpret_cast<void*>(descriptor),destination,source,1);
}
inline bool qa_soft_empty(uint64_t soft) {
 return !local_read<uint64_t>(soft) && !local_read<uint64_t>(soft+8) && !local_read<uint64_t>(soft+16) && !local_read<int32_t>(soft+32) && local_read<int32_t>(soft+36)>=0 && local_read<int32_t>(soft+36)<=4096;
}
inline bool qa_mime_restore(uint64_t base) {
 if(!qa_mime_default.address)return true;
 const auto cdo=call_identity(base,qa_mime_default);uint64_t descriptor=0;
 const auto soft=cdo?qa_battle_soft(base,cdo,"Mime_BattleStartParams",832,descriptor):0;
 if(!soft || descriptor!=qa_mime_descriptor || !qa_soft_copy_ready(base))return false;
 qa_soft_copy(base,descriptor,reinterpret_cast<void*>(soft),qa_mime_original);
 uint8_t empty[40]{};qa_soft_copy(base,descriptor,qa_mime_original,empty);
 qa_mime_default={};qa_mime_descriptor=0;return true;
}
inline void qa_mime_arena(uint64_t base,QAEncounterPacket& p) {
 if(p.version!=1||p.operation<2||p.operation>4||p.error||p.outcome||p.removed||p.reserved){p.error=1920;return;}
 if(p.operation==3){if(!qa_mime_restore(base)){p.error=1921;return;}p.outcome=1;return;}
 const auto w=call_identity(base,p.world),e=call_identity(base,p.enemy),gi=call_identity(base,p.gi),mime_target=call_identity(base,p.component);
 if(!w||!e||!gi||!mime_target||!zone_named(base,w,"Map_BattleTesting","/Game/QA/Map_BattleTesting")||zone_ref(base,w,"OwningGameInstance")!=gi||
 !exact_field_name(base,e+24,"BP_jRPG_EnemyWorld_Gault_C",1)||local_read<uint64_t>(local_read<uint64_t>(e+32)+32)!=w||!qa_soft_copy_ready(base)){p.error=1922;return;}
 const auto source=picto_field(base,e,"BattleMap_BP","SoftObjectProperty",2032,40);
 uint8_t empty[40]{};if(!source||std::memcmp(reinterpret_cast<void*>(source),empty,40)){p.error=1923;return;}
 uint64_t descriptor=0,soft=0;
 if(p.operation==2) {
  if(!zone_named(base,mime_target,"Default__BP_Dialogue_LUAct1_Mime_C","/Game/Narrative/Dialogs/LevelsDialogs/Lumiere/WalkAct1/BP_Dialogue_LUAct1_Mime") || !(local_read<uint32_t>(mime_target+8)&0x10)){p.error=1924;return;}
  soft=qa_battle_soft(base,mime_target,"Mime_BattleStartParams",832,descriptor);
  if(!soft){p.error=1925;return;}
  if(qa_mime_default.address) {
   if(call_identity(base,qa_mime_default)!=mime_target||!qa_soft_empty(soft)){p.error=1926;return;}
   p.outcome=1;return;
  }
  qa_soft_copy(base,descriptor,qa_mime_original,reinterpret_cast<void*>(soft));qa_mime_default=p.component;qa_mime_descriptor=descriptor;
 } else {
  if(!picto_class(base,mime_target,"AC_jRPG_BattleManager_C","/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_BattleManager")||
   local_read<uint64_t>(local_read<uint64_t>(local_read<uint64_t>(mime_target+32)+32)+32)!=w){p.error=1927;return;}
  soft=qa_battle_soft(base,mime_target,"CurrentBattleStartParams",1224,descriptor);if(!soft){p.error=1928;return;}
 }
 p.outcome=2;qa_soft_copy(base,descriptor,reinterpret_cast<void*>(soft),reinterpret_cast<void*>(source));
 if(!qa_soft_empty(soft)){p.error=1929;return;}p.outcome=1;
}
