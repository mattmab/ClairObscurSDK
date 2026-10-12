#pragma once
#include "picto_cost_script.h"
// Table map layout confirmed by native DoesDataTableRowExist disassembly and
// the live virtual accessor (lea rax,[rcx+30h]; ret), then 657 bounded row reads.
inline void picto_cost(uint64_t base,PictoProgressionPacket& p) {
 const auto table=call_identity(base,p.target),fn=call_identity(base,p.function),
 source=call_identity(base,p.source),panel=call_identity(base,p.panel),character=call_identity(base,p.game_instance);
 if(!table || !fn || !source || !panel || !character || !picto_cost_script(base,fn) ||
 !picto_class(base,table,"DataTable","/Script/Engine") || !exact_name(base,table+0x18,"DT_PassiveEffects") ||
 !exact_name(base,local_read<uint64_t>(table+0x20)+0x18,"/Game/Gameplay/Lumina/DT_PassiveEffects") ||
 !picto_class(base,source,"BP_PassiveEffectInstance_C","/Game/Gameplay/Lumina/Algorithm/BP_PassiveEffectInstance") ||
 !picto_class(base,character,"BP_CharacterData_C","/Game/Gameplay/CharacterData/BP_CharacterData") ||
 !picto_class(base,panel,"WBP_Panel_Pictos_C","/Game/UI/Widgets/InGame_Menu/Pictos_Panel/WBP_Panel_Pictos")){p.error=1720;return;}
 const auto active=picto_field(base,panel,"bIsActive","BoolProperty",872,1),
 current=picto_field(base,panel,"CurrentCharacterData","ObjectProperty",1216,8),
 owner=picto_field(base,source,"OwnerData","ObjectProperty",128,8),
 idat=picto_field(base,source,"PassiveEffectID","NameProperty",48,8);
 if(!active || local_read<uint8_t>(active)!=1 || !current || local_read<uint64_t>(current)!=character ||
 !owner || local_read<uint64_t>(owner)!=character || !idat){p.error=1721;return;}
 uint64_t desc=0;auto definition=picto_field(base,source,"PassiveDefinition","StructProperty",56,72,&desc);
 const auto rowstruct=local_read<uint64_t>(table+40);
 if(!definition || !rowstruct || local_read<uint64_t>(desc+0x70)!=rowstruct ||
 !exact_name(base,rowstruct+0x18,"FPassiveEffect") || local_read<int32_t>(rowstruct+0x58)!=72){p.error=1722;return;}
 bool cost_schema=false;
 for(auto f=local_read<uint64_t>(rowstruct+0x50),n=uint64_t(0);f && ++n<64;f=local_read<uint64_t>(f+0x18)) {
  if(exact_name(base,f+0x20,"LuminaCost_15_BC10A93D48987A14F96279AC521E94CF"))
   cost_schema=local_read<uint64_t>(f+0x10)==(rowstruct|1) && exact_name(base,local_read<uint64_t>(f+8),"IntProperty") && local_read<int32_t>(f+0x44)==48 && local_read<int32_t>(f+0x34)==4 && local_read<int32_t>(f+0x30)==1;
 }
 const uint8_t accessor[]={0x48,0x8d,0x41,0x30,0xc3};
 const auto getmap=local_read<uint64_t>(local_read<uint64_t>(table)+0x2d8);
 if(!cost_schema || !getmap || std::memcmp(reinterpret_cast<void*>(getmap),accessor,sizeof(accessor))){p.error=1723;return;}
 const auto map=table+48,data=local_read<uint64_t>(map),heap=local_read<uint64_t>(map+32),mask=heap?heap:map+16;
 const auto count=local_read<int32_t>(map+8),cap=local_read<int32_t>(map+12),bits=local_read<int32_t>(map+40),bitcap=local_read<int32_t>(map+44),free=local_read<int32_t>(map+52);
 if(count<0 || cap<count || cap>4096 || bits!=count || bitcap<bits || bitcap>4096 || free<0 || free>count || (!heap && bitcap>128) || !data || (data&7)){p.error=1724;return;}
 const auto id=local_read<uint64_t>(idat);uint64_t row=0;int live=0,found=0;
 for(int i=0;i<count;++i) {
  if(!(local_read<uint32_t>(mask+uint64_t(i/32)*4)&(uint32_t(1)<<(i%32))))continue;
  ++live;auto at=data+uint64_t(i)*24;
  if(local_read<uint64_t>(at)==id){++found;row=local_read<uint64_t>(at+8);}
 }
 if(live!=count-free || found!=1 || !row || (row&7) || local_read<int32_t>(row+48)!=p.expected){p.error=1725;return;}
 const auto passiveclass=local_read<uint64_t>(source+0x10),characterclass=local_read<uint64_t>(character+0x10);
 if(local_read<uint64_t>(fn+0x20)!=characterclass){p.error=1726;return;}
 // Preflight every cached copy and character before the first write.
 uint64_t copies[2048]{},characters[64]{};int nc=0,nh=0;
 const int objects=local_read<int32_t>(base+0x9361b84),chunks_count=local_read<int32_t>(base+0x9361b8c);
 const auto chunks=local_read<uint64_t>(base+0x9361b70);
 if(objects<0 || objects>1000000 || chunks_count<=((objects-1)>>16) || chunks_count>32 || !chunks){p.error=1727;return;}
 for(int i=0;i<objects;++i) {
  const auto chunk=local_read<uint64_t>(chunks+uint64_t(i>>16)*8);if(!chunk){p.error=1727;return;}
  const auto slot=chunk+uint64_t(i&65535)*24,obj=local_read<uint64_t>(slot);
  if(!obj || (local_read<uint32_t>(obj+8)&0x30))continue;
  const auto cls=local_read<uint64_t>(obj+0x10);
  if(cls!=passiveclass && cls!=characterclass)continue;
  if(local_read<int32_t>(obj+12)!=i || !call_identity(base,CallIdentity{i,local_read<int32_t>(slot+16),obj})){p.error=1727;return;}
  if(cls==passiveclass && local_read<uint64_t>(obj+48)==id) {
   if(nc>=2048 || local_read<int32_t>(obj+104)!=p.expected){p.error=1728;return;}copies[nc++]=obj+104;
  } else if(cls==characterclass) {
   auto dispatch=local_read<uint64_t>(local_read<uint64_t>(obj)+0x268);
   if(nh>=64 || (dispatch!=base+0x1393330 && dispatch!=base+0x332bb90)){p.error=1729;return;}
   characters[nh++]=obj;
  }
 }
 if(!nc || !nh){p.error=1730;return;}
 p.outcome=2;
 std::memcpy(reinterpret_cast<void*>(row+48),&p.value,4);
 for(int i=0;i<nc;++i)std::memcpy(reinterpret_cast<void*>(copies[i]),&p.value,4);
 for(int i=0;i<nh;++i) {
  alignas(16) uint8_t args[4096]{};auto obj=characters[i];auto dispatch=local_read<uint64_t>(local_read<uint64_t>(obj)+0x268);
  reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(dispatch)(reinterpret_cast<void*>(obj),reinterpret_cast<void*>(fn),args);
 }
 p.observed=local_read<int32_t>(row+48);
 if(p.observed!=p.value){p.error=1731;return;}
 for(int i=0;i<nc;++i)if(local_read<int32_t>(copies[i])!=p.value){p.error=1731;return;}
 p.outcome=1;
}
