#pragma once
#include "inventory_reward_packet.h"
namespace e33_inventory_reward {
struct Dispatcher {
 bool unknown=false;
 bool map_schema(uint64_t b,uint64_t d,const char*type,int width,int stride)const{
  const auto k=local_read<uint64_t>(d+0x70),v=local_read<uint64_t>(d+0x78);
  return k&&v&&!(local_read<uint8_t>(d+0x98)&1)&&local_read<uint64_t>(k+16)==d&&local_read<uint64_t>(v+16)==d&&
   exact_name(b,local_read<uint64_t>(k+8),"NameProperty")&&exact_name(b,local_read<uint64_t>(v+8),type)&&
   local_read<int32_t>(k+0x34)==8&&local_read<int32_t>(v+0x34)==width&&local_read<int32_t>(k+0x44)==0&&local_read<int32_t>(v+0x44)==8&&
   local_read<int32_t>(d+0x80)==8&&local_read<int32_t>(d+0x8c)==stride;
 }
 bool victory(uint64_t b,uint64_t gi,bool&won,const char*quest_name,const char*objective_name)const{
  won=false;const auto quest=zone_ref(b,gi,"QuestSystem");
  if(!quest||!picto_class(b,quest,"BP_QuestSystem_C","/Game/Gameplay/Quests/System/BP_QuestSystem"))return false;
  uint64_t d=0;const auto map=picto_field(b,quest,"QuestStatuses","MapProperty",40,80,&d);
  if(!map||!map_schema(b,d,"StructProperty",88,104))return false;
  const auto st=local_read<uint64_t>(local_read<uint64_t>(d+0x78)+0x70);
  if(!st||!exact_name(b,st+24,"S_QuestStatusData"))return false;
  const auto inner=picto_struct_field(b,st,"ObjectivesStatus_8_EA1232C14DA1F6DDA84EBA9185000F56","MapProperty",0,80);
  if(!inner||!map_schema(b,inner,"ByteProperty",1,20))return false;
  uint64_t q=0,o=0;if(!e33_blueprint_names::resolve(b,quest_name,q)||!e33_blueprint_names::resolve(b,objective_name,o))return false;
  PictoSparseView outer{};if(!picto_sparse(map,104,512,outer))return false;unsigned matches=0;
  for(int i=0;i<outer.count;++i)if(outer.active(i)){
   const auto at=outer.data+uint64_t(i)*104;if(local_read<uint64_t>(at)!=q)continue;
   if(++matches>1)return false;PictoSparseView objectives{};if(!picto_sparse(at+8,20,512,objectives))return false;unsigned found=0;
   for(int j=0;j<objectives.count;++j)if(objectives.active(j)){
    const auto row=objectives.data+uint64_t(j)*20;if(local_read<uint64_t>(row)!=o)continue;
    if(++found>1)return false;won=local_read<uint8_t>(row+8)==3;
   }
  }return true;
 }
 bool map_object(uint64_t b,uint64_t object,const char*field,int offset,uint64_t name,uint64_t&value)const{
  uint64_t d=0;const auto map=picto_field(b,object,field,"MapProperty",offset,80,&d);
  if(!map||!map_schema(b,d,"ObjectProperty",8,24))return false;
  PictoSparseView view{};if(!picto_sparse(map,24,4096,view))return false;
  unsigned found=0;value=0;for(int i=0;i<view.count;++i)if(view.active(i)){
   const auto at=view.data+uint64_t(i)*24;if(local_read<uint64_t>(at)==name){if(++found>1)return false;value=local_read<uint64_t>(at+8);}
  }return found==1&&call_capture(b,value).address;
 }
 bool equipped(uint64_t b,uint64_t character,uint64_t&weapon)const{
  uint64_t d=0;const auto map=picto_field(b,character,"EquipmentInstancePerSlot","MapProperty",2112,80,&d);
  if(!map||local_read<uint32_t>(d+0x8c)!=24)return false;
  const auto key=local_read<uint64_t>(d+0x70),value=local_read<uint64_t>(d+0x78);
  if(!key||!value||!exact_name(b,local_read<uint64_t>(key+8),"StructProperty")||!exact_name(b,local_read<uint64_t>(value+8),"ObjectProperty")||
   local_read<int32_t>(key+0x34)!=8||local_read<int32_t>(value+0x34)!=8||local_read<int32_t>(value+0x44)!=8)return false;
  const auto st=local_read<uint64_t>(key+0x70);
  if(!e33_mesh::named(b,st,"FEquipmentSlot","/Game/Gameplay/Inventory/FEquipmentSlot")||
   !picto_struct_field(b,st,"ItemType_4_419B69C74E6D605B52FA82A76F128C96","ByteProperty",0,1)||
   !picto_struct_field(b,st,"SlotIndex_7_4AC21CC043F87846335A25B9212005AB","IntProperty",4,4))return false;
  PictoSparseView view{};if(!picto_sparse(map,24,128,view))return false;
  weapon=0;unsigned found=0;for(int i=0;i<view.count;++i)if(view.active(i)){
   const auto at=view.data+uint64_t(i)*24;
   if(local_read<uint8_t>(at)==1&&local_read<int32_t>(at+4)==0){if(++found>1)return false;weapon=local_read<uint64_t>(at+8);}
  }return true;
 }
 void equip_weapon(uint64_t b,Packet&p){
  e33_story_action::Dispatcher proof;proof.base=b;proof.gi=p.gi;std::memcpy(proof.guid,p.guid,16);
  uint64_t character_name=0,itemid=0,character=0,item=0;
  const auto system=zone_ref(b,p.gi.address,"InventorySystem");
  if(!proof.bound()||!e33_blueprint_names::resolve(b,p.character,character_name)||!e33_blueprint_names::resolve(b,p.item,itemid)||
   !map_object(b,p.gi.address,"CharactersCollection",2344,character_name,character)||character!=p.manager.address||
   !picto_class(b,character,"BP_CharacterData_C","/Game/Gameplay/CharacterData/BP_CharacterData")||local_read<uint64_t>(character+32)!=p.gi.address||
   !system||!picto_class(b,system,"BP_ItemUpgradeSystem_C","/Game/Gameplay/Pictos/BP_ItemUpgradeSystem")||
   !map_object(b,system,"ItemInstances",576,itemid,item)||!picto_class(b,item,"BP_ItemInstance_Gear_Weapon_C","/Game/Gameplay/Pictos/BP_ItemInstance_Gear_Weapon")||
   !picto_legacy_owned(b,p.gi.address,itemid,true)){p.error=4240;return;}
  const auto hardcoded=picto_field(b,character,"HardcodedNameID","NameProperty",48,8),quantity=picto_field(b,item,"Quantity","IntProperty",360,4),id=picto_field(b,item,"ItemDefinitionID","NameProperty",48,8);
  const auto fn=p.function.address;
  if(!hardcoded||local_read<uint64_t>(hardcoded)!=character_name||!quantity||local_read<int32_t>(quantity)!=1||!id||local_read<uint64_t>(id)!=itemid||
   !exact_name(b,fn+24,"EquipItemInstanceInSlot")||
   local_read<uint64_t>(fn+32)!=local_read<uint64_t>(character+16)||local_read<uint16_t>(fn+0xb6)!=16||local_read<uint32_t>(fn+0xb0)!=209846272U||local_read<uint64_t>(fn+0xd8)!=b+0x13937a0){p.error=4241;return;}
  const auto slot=picto_struct_field(b,fn,"Slot","StructProperty",0,8),arg=picto_struct_field(b,fn,"Item","ObjectProperty",8,8);
  if(!slot||!arg||!e33_mesh::named(b,local_read<uint64_t>(slot+0x70),"FEquipmentSlot","/Game/Gameplay/Inventory/FEquipmentSlot")){p.error=4242;return;}
  uint64_t previous=0;if(!equipped(b,character,previous)){p.error=4243;return;}
  if(previous){if(previous!=item){p.error=4244;return;}p.outcome=1;p.state=1;return;}
  const auto dispatch=local_read<uint64_t>(local_read<uint64_t>(character)+0x268);
  if(dispatch!=b+0x1393330&&dispatch!=b+0x332bb90){p.error=4245;return;}
  alignas(16)uint8_t args[4096]{};args[0]=1;std::memcpy(args+8,&item,8);
  unknown=true;reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(dispatch)(reinterpret_cast<void*>(character),reinterpret_cast<void*>(fn),args);
  uint64_t observed=0;if(!proof.bound()||!equipped(b,character,observed)||observed!=item){p.error=uncertain;return;}
  unknown=false;p.outcome=2;p.state=1;
 }
 template<class Pool>void run(uint64_t b,uint64_t s,Pool&pool,Packet&p,e33_story_items::Dispatcher&items){
  if(unknown){p.error=uncertain;return;}
  if(!valid(p)){p.error=rejected;return;}
  const CallIdentity ids[]={p.gi,p.manager,p.function};for(unsigned i=0;i<3;++i)if(!call_identity(b,ids[i])||!pool.owns_object(s,p.leases[i],ids[i].address)){p.error=4232;return;}
  if(p.mode==2){equip_weapon(b,p);return;}
  e33_story_action::Dispatcher proof;proof.base=b;proof.gi=p.gi;std::memcpy(proof.guid,p.guid,16);
  e33_story_rewards::Dispatcher signature;uint64_t item=0;
  if(!proof.bound()||!items.current()||!e33_blueprint_names::resolve(b,p.item,item)||!items.definition(item)||
   !picto_class(b,p.manager.address,"AC_jRPG_InventoryManager_C","/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_InventoryManager")||
   zone_ref(b,p.manager.address,"GameInstanceReference")!=p.gi.address||!signature.schema(b,p.function.address)){p.error=4233;return;}
  bool won=p.mode==1;if(p.mode==0&&!victory(b,p.gi.address,won,p.quest,p.objective)){p.error=4234;return;}
  if(!won){p.outcome=0;p.state=1;return;}
  if(picto_legacy_owned(b,p.gi.address,item,true)){p.outcome=1;p.state=1;return;}
  if(!picto_legacy_owned(b,p.gi.address,item,false)){p.error=rejected;return;}
  const auto dispatch=local_read<uint64_t>(local_read<uint64_t>(p.manager.address)+0x268);
  if(dispatch!=b+0x1393330&&dispatch!=b+0x332bb90){p.error=rejected;return;}
  alignas(16)uint8_t args[32]{};std::memcpy(args,&item,8);const int amount=1;std::memcpy(args+8,&amount,4);
  unknown=true;
  reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(dispatch)(reinterpret_cast<void*>(p.manager.address),reinterpret_cast<void*>(p.function.address),args);
  if(!proof.bound()||!picto_legacy_owned(b,p.gi.address,item,true)){p.error=uncertain;return;}
  unknown=false;p.outcome=2;p.state=1;
 }
};
}

