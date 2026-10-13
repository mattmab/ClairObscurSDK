#pragma once
#include "picto_progression_protocol.h"
inline bool picto_class(uint64_t base,uint64_t object,const char* name,const char* package) {
 const auto cls=local_read<uint64_t>(object+0x10);
 return exact_name(base,cls+0x18,name) && exact_name(base,local_read<uint64_t>(cls+0x20)+0x18,package) && !(local_read<uint32_t>(object+8)&0x30);
}
inline uint64_t picto_field(uint64_t base,uint64_t object,const char* name,const char* type,int offset,int width,uint64_t* descriptor=nullptr) {
 auto cls=local_read<uint64_t>(object+0x10); unsigned owners=0;
 for(;cls && ++owners<32;cls=local_read<uint64_t>(cls+0x40)) {
  unsigned fields=0;
  for(auto f=local_read<uint64_t>(cls+0x50);f && ++fields<512;f=local_read<uint64_t>(f+0x18)) {
   if(!exact_name(base,f+0x20,name))continue;
   if(local_read<uint64_t>(f+0x10)!=(cls|1) || !exact_name(base,local_read<uint64_t>(f+8),type) ||
      local_read<int32_t>(f+0x44)!=offset || local_read<int32_t>(f+0x34)!=width || local_read<int32_t>(f+0x30)!=1)return 0;
   if(descriptor)*descriptor=f;
   return object+offset;
  }
 }
 return 0;
}
inline bool picto_mastery(uint64_t base,uint64_t character,uint64_t id,int32_t& steps,bool& learnt) {
 uint64_t descriptor=0;
 auto map=picto_field(base,character,"SharedPassiveEffectProgression","MapProperty",3816,80,&descriptor);
 if(!map || (local_read<uint8_t>(descriptor+0x98)&1))return false;
 const auto key=local_read<uint64_t>(descriptor+0x70), value=local_read<uint64_t>(descriptor+0x78);
 if(!key || !value || !exact_name(base,local_read<uint64_t>(key+8),"NameProperty") ||
 !exact_name(base,local_read<uint64_t>(value+8),"StructProperty") || local_read<uint64_t>(key+0x10)!=descriptor ||
 local_read<uint64_t>(value+0x10)!=descriptor || local_read<uint32_t>(key+0x34)!=8 || local_read<uint32_t>(value+0x34)!=16 ||
 !exact_name(base,local_read<uint64_t>(value+0x70)+0x18,"FPassiveEffectProgression"))return false;
 const auto vo=local_read<int32_t>(descriptor+0x80),stride=local_read<int32_t>(descriptor+0x8c);
 if(vo<8 || vo>32 || stride<vo+16 || stride>64)return false;
 const auto count=local_read<int32_t>(map+8),cap=local_read<int32_t>(map+12),bits=local_read<int32_t>(map+40),
 bitcap=local_read<int32_t>(map+44),free=local_read<int32_t>(map+52);
 const auto data=local_read<uint64_t>(map),heap=local_read<uint64_t>(map+32),mask=heap?heap:map+16;
 if(count<0 || cap<count || cap>4096 || bits!=count || bitcap<bits || bitcap>4096 || free<0 || free>count ||
 (!heap && bitcap>128) || (count && (!data || (data&7))))return false;
 int live=0,found=0;steps=0;learnt=false;
 for(int i=0;i<count;++i) {
  if(!(local_read<uint32_t>(mask+uint64_t(i/32)*4)&(uint32_t(1)<<(i%32))))continue;
  ++live;auto at=data+uint64_t(i)*stride;
  if(local_read<uint64_t>(at)!=id)continue;
  ++found;at+=vo;
  if(local_read<uint64_t>(at)!=id || local_read<uint8_t>(at+8)>1)return false;
  learnt=local_read<uint8_t>(at+8)!=0;steps=local_read<int32_t>(at+12);
 }
 return live==count-free && found<=1;
}
inline bool picto_progression_script(uint64_t base,uint64_t function,uint32_t operation) {
 return operation==1 ? picto_stable_script(base,function,1) : operation==2 && picto_stable_script(base,function,5);
}
#include "picto_cost.h"
#include "picto_inventory.h"
// Read an existing Byte->Double stat entry; no allocator or raw write exposure.
inline bool picto_stat_entry(uint64_t base,uint64_t object,const char* name,int offset,uint8_t stat,double& result,int& entry) {
 uint64_t descriptor=0;const auto map=picto_field(base,object,name,"MapProperty",offset,80,&descriptor);
 if(!map || (local_read<uint8_t>(descriptor+0x98)&1))return false;
 const auto key=local_read<uint64_t>(descriptor+0x70),value=local_read<uint64_t>(descriptor+0x78);
 if(!key || !value || local_read<uint64_t>(key+0x10)!=descriptor || local_read<uint64_t>(value+0x10)!=descriptor ||
 !exact_name(base,local_read<uint64_t>(key+8),"ByteProperty") || !exact_name(base,local_read<uint64_t>(value+8),"DoubleProperty") ||
 local_read<int32_t>(key+0x30)!=1 || local_read<int32_t>(value+0x30)!=1 || local_read<int32_t>(key+0x34)!=1 ||
 local_read<int32_t>(value+0x34)!=8 || local_read<int32_t>(key+0x44)!=0)return false;
 const auto vo=local_read<int32_t>(descriptor+0x80),stride=local_read<int32_t>(descriptor+0x8c);
 if(vo!=8 || local_read<int32_t>(value+0x44)!=vo || stride!=24)return false;
 const auto data=local_read<uint64_t>(map),heap=local_read<uint64_t>(map+32),mask=heap?heap:map+16;
 const auto count=local_read<int32_t>(map+8),cap=local_read<int32_t>(map+12),bits=local_read<int32_t>(map+40),
 bitcap=local_read<int32_t>(map+44),free=local_read<int32_t>(map+52);
 if(count<0 || count>cap || cap>64 || bits!=count || bitcap<bits || bitcap>128 || free<0 || free>count ||
 (count && (!data || (data&7))))return false;
 int live=0,found=0;uint16_t seen=0;result=0;entry=-1;
 for(int i=0;i<count;++i) {
  if(!(local_read<uint32_t>(mask+uint64_t(i/32)*4)&(uint32_t(1)<<(i%32))))continue;
  ++live;const auto at=data+uint64_t(i)*stride;const auto k=local_read<uint8_t>(at);
  if(k>15 || (seen&(1U<<k)))return false;seen|=uint16_t(1U<<k);
  if(k==stat){++found;entry=i;result=local_read<double>(at+vo);}
 }
 return live==count-free && found<=1 && std::isfinite(result);
}
inline bool picto_stat_value(uint64_t base,uint64_t object,const char* name,int offset,uint8_t stat,double& result) {
 int entry=-1;return picto_stat_entry(base,object,name,offset,stat,result,entry) && entry>=0;
}
#include "picto_stat_hash.h"
#include "picto_stat_remove.h"
inline void picto_clear_stat(uint64_t base,PictoProgressionPacket& p) {
 const auto target=call_identity(base,p.target),function=call_identity(base,p.function);
 double multiplier=0,current=0;
 if(!target || !function || !picto_class(base,target,"BP_ItemInstance_Gear_Pictos_C","/Game/Gameplay/Pictos/BP_ItemInstance_Gear_Pictos") ||
 !picto_stable_script(base,function,7) || !call_derives(base,local_read<uint64_t>(target+0x10),local_read<uint64_t>(function+0x20)) ||
 !picto_stat_value(base,target,"BaseStatsMultipliers",464,uint8_t(p.value),multiplier) || multiplier!=0. ||
 !picto_stat_value(base,target,"CurrentStats",376,uint8_t(p.value),current) || current!=double(p.expected)) {p.error=1740;return;}
 const auto dispatch=local_read<uint64_t>(local_read<uint64_t>(target)+0x268);
 if(dispatch!=base+0x1393330 && dispatch!=base+0x332bb90){p.error=1741;return;}
 alignas(16) uint8_t args[4096]{};args[0]=uint8_t(p.value); // Value=0, Reason=empty FString.
 p.outcome=2;
 reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(dispatch)(reinterpret_cast<void*>(target),reinterpret_cast<void*>(function),args);
 if(!picto_stat_value(base,target,"CurrentStats",376,uint8_t(p.value),current) || current!=0.){p.error=1742;return;}
 p.observed=0;p.outcome=1;
}
inline void picto_progression(uint64_t base,PictoProgressionPacket& p) {
 if(!valid_picto_progression(p)){p.error=1700;return;}
 if(p.operation==12){picto_remove_stat(base,p);return;}
 if(p.operation==10){picto_inventory(base,p);return;}
 if(p.operation==11){picto_refresh_inventory_panel(base,p);return;}
 if(p.operation==9){picto_clear_stat(base,p);return;}
 const bool startup=p.operation>=4;
 const auto operation=p.operation>=6?3:startup?p.operation-3:p.operation;
 if(operation==3){picto_cost(base,p);return;}
 const auto target=call_identity(base,p.target), function=call_identity(base,p.function),panel=call_identity(base,p.panel);
 if(!target || !function || (!startup && !panel) || !exact_name(base,local_read<uint64_t>(function+0x10)+0x18,"Function") || !picto_progression_script(base,function,operation) ||
 (!startup && !picto_class(base,panel,"WBP_Panel_Pictos_C","/Game/UI/Widgets/InGame_Menu/Pictos_Panel/WBP_Panel_Pictos"))){p.error=1701;return;}
 if(local_read<uint64_t>(function+0xd8)!=base+0x13937a0 || local_read<uint16_t>(function+0xb8)!=65535 ||
 !call_derives(base,local_read<uint64_t>(target+0x10),local_read<uint64_t>(function+0x20))){p.error=1707;return;}
 auto active=startup?0:picto_field(base,panel,"bIsActive","BoolProperty",872,1);
 if(!startup && (!active || local_read<uint8_t>(active)!=1)){p.error=1708;return;}
 // Typed script operands are resolved and checked against stable symbolic profiles.
 auto dispatch=local_read<uint64_t>(local_read<uint64_t>(target)+0x268);
 if(dispatch!=base+0x1393330 && dispatch!=base+0x332bb90){p.error=1702;return;}
 alignas(16) uint8_t args[4096]{};
 if(operation==1) {
  if(!picto_class(base,target,"BP_ItemInstance_Gear_Pictos_C","/Game/Gameplay/Pictos/BP_ItemInstance_Gear_Pictos")){p.error=1703;return;}
  auto level=picto_field(base,target,"CurrentLevel","IntProperty",456,4);
  if(!level || local_read<int32_t>(level)!=p.expected){p.error=1704;return;}
  std::memcpy(args,&p.value,4); // DebugReason is an empty, non-owning FString.
  p.outcome=2;
  reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(dispatch)(reinterpret_cast<void*>(target),reinterpret_cast<void*>(function),args);
  p.outcome=1;p.observed=local_read<int32_t>(level);
  if(p.observed!=p.value)p.error=1705;
 } else {
  const auto source=call_identity(base,p.source),gi=call_identity(base,p.game_instance);
  if(!source || !gi || !picto_class(base,gi,"BP_jRPG_GI_Custom_C","/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_GI_Custom") || !picto_class(base,target,"BP_CharacterData_C","/Game/Gameplay/CharacterData/BP_CharacterData") ||
  !(startup ? picto_class(base,source,"BP_ItemInstance_Gear_Pictos_C","/Game/Gameplay/Pictos/BP_ItemInstance_Gear_Pictos") : picto_class(base,source,"BP_PassiveEffectInstance_C","/Game/Gameplay/Lumina/Algorithm/BP_PassiveEffectInstance"))){p.error=1706;return;}
  const auto owner=startup?0:picto_field(base,source,"OwnerData","ObjectProperty",128,8),
   current=startup?0:picto_field(base,panel,"CurrentCharacterData","ObjectProperty",1216,8),
   id_at=picto_field(base,source,startup?"ItemDefinitionID":"PassiveEffectID","NameProperty",48,8);
  if(!id_at || (!startup && (!owner || local_read<uint64_t>(owner)!=target || !current || local_read<uint64_t>(current)!=target))){p.error=1709;return;}
  const auto id=local_read<uint64_t>(id_at);int32_t before=0;bool learnt=false;
  if(!id || !picto_mastery(base,gi,id,before,learnt) || before!=p.expected){p.error=1710;return;}
  std::memcpy(args,&id,8);std::memcpy(args+8,&p.value,4);
  p.outcome=2;
  reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(dispatch)(reinterpret_cast<void*>(target),reinterpret_cast<void*>(function),args);
  p.outcome=1;
  if(!picto_mastery(base,gi,id,p.observed,learnt) || p.observed!=p.value)p.error=1711;

 }
}
inline void picto_batch_level(uint64_t base,const CallIdentity& system_id,PictoProgressionPacket& p) {
 const auto system=call_identity(base,system_id),item=call_identity(base,p.target);
 if(!system || !item || !picto_class(base,system,"BP_ItemUpgradeSystem_C","/Game/Gameplay/Pictos/BP_ItemUpgradeSystem")) {p.error=1776;return;}
 const auto id_at=picto_field(base,item,"ItemDefinitionID","NameProperty",48,8),level=picto_field(base,item,"CurrentLevel","IntProperty",456,4);
 uint64_t owned=0;
 if(!id_at || !level || !picto_owned_item(base,system,local_read<uint64_t>(id_at),owned) || owned!=item) {p.error=1777;return;}
 p.expected=local_read<int32_t>(level);
 if(p.expected<1 || p.expected>33 || p.value<1 || p.value>33){p.error=1704;return;}
 if(p.expected==p.value){p.observed=p.value;p.outcome=1;return;}
 picto_progression(base,p);
}

// Each queued mastery edit revalidates ownership and reads the live threshold.
inline void picto_batch_mastery(uint64_t base,const CallIdentity& table_id,bool mastered,PictoProgressionPacket& p) {
 const auto gi=call_identity(base,p.game_instance),item=call_identity(base,p.source),table=call_identity(base,table_id);
 if(!gi || !item || !table || !picto_class(base,gi,"BP_jRPG_GI_Custom_C","/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_GI_Custom") ||
 !picto_class(base,item,"BP_ItemInstance_Gear_Pictos_C","/Game/Gameplay/Pictos/BP_ItemInstance_Gear_Pictos")){p.error=1778;return;}
 const auto sysref=picto_field(base,gi,"InventorySystem","ObjectProperty",3296,8),id_at=picto_field(base,item,"ItemDefinitionID","NameProperty",48,8);
 const auto system=sysref?local_read<uint64_t>(sysref):0;
 uint64_t owned=0;
 if(!system || !call_identity(base,call_capture(base,system)) || !picto_class(base,system,"BP_ItemUpgradeSystem_C","/Game/Gameplay/Pictos/BP_ItemUpgradeSystem") ||
 !id_at || !picto_owned_item(base,system,local_read<uint64_t>(id_at),owned) || owned!=item){p.error=1777;return;}
 const auto id=local_read<uint64_t>(id_at);bool learnt=false;
 if(!id || !picto_mastery(base,gi,id,p.expected,learnt) || p.expected<0){p.error=1710;return;}
 if(learnt==mastered && (mastered || p.expected==0)){p.observed=p.expected;p.outcome=1;return;}
 uint64_t row=0;int offset=-1;
 if(const auto error=picto_passive_row(base,table,id,row,offset)){p.error=error;return;}
 if(offset<0 || offset>68 || (offset&3)){p.error=1732;return;}
 const auto threshold=local_read<int32_t>(row+offset);
 if(threshold<1 || threshold>100){p.error=1779;return;}
 p.value=mastered?threshold:0;
 picto_progression(base,p);
 if(!p.error && (!picto_mastery(base,gi,id,p.observed,learnt) || learnt!=mastered || p.observed!=p.value))p.error=1711;
}
