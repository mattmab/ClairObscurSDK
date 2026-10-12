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
inline void picto_progression(uint64_t base,PictoProgressionPacket& p) {
 if(!valid_picto_progression(p)){p.error=1700;return;}
 if(p.operation==3){picto_cost(base,p);return;}
 const auto target=call_identity(base,p.target), function=call_identity(base,p.function),panel=call_identity(base,p.panel);
 if(!target || !function || !panel || !exact_name(base,local_read<uint64_t>(function+0x10)+0x18,"Function") || !picto_progression_script(base,function,p.operation) ||
 !picto_class(base,panel,"WBP_Panel_Pictos_C","/Game/UI/Widgets/InGame_Menu/Pictos_Panel/WBP_Panel_Pictos")){p.error=1701;return;}
 if(local_read<uint64_t>(function+0xd8)!=base+0x13937a0 || local_read<uint16_t>(function+0xb8)!=65535 ||
 !call_derives(base,local_read<uint64_t>(target+0x10),local_read<uint64_t>(function+0x20))){p.error=1707;return;}
 auto active=picto_field(base,panel,"bIsActive","BoolProperty",872,1);
 if(!active || local_read<uint8_t>(active)!=1){p.error=1708;return;}
 // Typed script operands are resolved and checked against stable symbolic profiles.
 auto dispatch=local_read<uint64_t>(local_read<uint64_t>(target)+0x268);
 if(dispatch!=base+0x1393330 && dispatch!=base+0x332bb90){p.error=1702;return;}
 alignas(16) uint8_t args[4096]{};
 if(p.operation==1) {
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
  !picto_class(base,source,"BP_PassiveEffectInstance_C","/Game/Gameplay/Lumina/Algorithm/BP_PassiveEffectInstance")){p.error=1706;return;}
  const auto owner=picto_field(base,source,"OwnerData","ObjectProperty",128,8),
   current=picto_field(base,panel,"CurrentCharacterData","ObjectProperty",1216,8),
   id_at=picto_field(base,source,"PassiveEffectID","NameProperty",48,8);
  if(!owner || !current || !id_at || local_read<uint64_t>(owner)!=target || local_read<uint64_t>(current)!=target){p.error=1709;return;}
  const auto id=local_read<uint64_t>(id_at);int32_t before=0;bool learnt=false;
  if(!id || !picto_mastery(base,gi,id,before,learnt) || before!=p.expected){p.error=1710;return;}
  std::memcpy(args,&id,8);std::memcpy(args+8,&p.value,4);
  p.outcome=2;
  reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(dispatch)(reinterpret_cast<void*>(target),reinterpret_cast<void*>(function),args);
  p.outcome=1;
  if(!picto_mastery(base,gi,id,p.observed,learnt) || p.observed!=p.value)p.error=1711;

 }
}
