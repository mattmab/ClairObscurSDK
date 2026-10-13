#pragma once
#ifndef E33_PICTO_SCHEMA_FIXTURE
#include "picto_shipping_assert.h"
inline void picto_refresh_inventory_panel(uint64_t base,PictoProgressionPacket& p) {
 const auto panel=call_identity(base,p.target),fn=call_identity(base,p.function),character=call_identity(base,p.source);
 if(!panel || !fn || !character || !picto_class(base,panel,"WBP_Panel_Pictos_C","/Game/UI/Widgets/InGame_Menu/Pictos_Panel/WBP_Panel_Pictos") ||
 !picto_class(base,character,"BP_CharacterData_C","/Game/Gameplay/CharacterData/BP_CharacterData") || !picto_stable_script(base,fn,10)) {p.error=1763;return;}
 const auto active=picto_field(base,panel,"bIsActive","BoolProperty",872,1),current=picto_field(base,panel,"CurrentCharacterData","ObjectProperty",1216,8);
 if(!active || local_read<uint8_t>(active)!=1 || !current || local_read<uint64_t>(current)!=character){p.error=1764;return;}
 const auto dispatch=local_read<uint64_t>(local_read<uint64_t>(panel)+0x268);
 if(dispatch!=base+0x1393330 && dispatch!=base+0x332bb90){p.error=1761;return;}
 alignas(16) uint8_t args[4096]{};std::memcpy(args,&character,8);p.outcome=2;
 reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(dispatch)(reinterpret_cast<void*>(panel),reinterpret_cast<void*>(fn),args);
 if(local_read<uint64_t>(current)!=character){p.error=1764;return;}
 p.outcome=1;
}
// Narrow game-thread ownership operation. Never expose raw map writes or save calls.
struct PictoSparseView {
 uint64_t data=0,mask=0;int count=0,free=0,stride=0;
 bool active(int i) const {return (local_read<uint32_t>(mask+uint64_t(i/32)*4)&(uint32_t(1)<<(i%32)))!=0;}
};
inline bool picto_sparse(uint64_t map,int stride,int limit,PictoSparseView& out) {
 const auto n=local_read<int32_t>(map+8),cap=local_read<int32_t>(map+12),bits=local_read<int32_t>(map+40),bc=local_read<int32_t>(map+44),free=local_read<int32_t>(map+52);
 const auto data=local_read<uint64_t>(map),heap=local_read<uint64_t>(map+32);
 if(n<0 || n>cap || cap>limit || bits!=n || bc<bits || bc>limit || free<0 || free>n || (!heap && bc>128) || (n && (!data || (data&7))))return false;
 out={data,heap?heap:map+16,n,free,stride};int live=0;
 for(int i=0;i<n;++i)if(out.active(i))++live;
 return live==n-free;
}
#endif
inline uint64_t picto_struct_field(uint64_t base,uint64_t owner,const char* name,const char* type,int offset,int width) {
 for(auto f=local_read<uint64_t>(owner+0x50),n=uint64_t(0);f && ++n<256;f=local_read<uint64_t>(f+0x18))
  if(exact_name(base,f+0x20,name))return local_read<uint64_t>(f+0x10)==(owner|1) &&
   exact_name(base,local_read<uint64_t>(f+8),type) && local_read<int32_t>(f+0x44)==offset &&
   local_read<int32_t>(f+0x34)==width && local_read<int32_t>(f+0x30)==1?f:0;
 return 0;
}
inline bool picto_static_schema(uint64_t base,uint64_t st) {
 // UStruct PropertiesSize is the unpadded extent (last bool at 297).
 // FStructProperty element width / inventory stride remains aligned to 304.
 return st && exact_name(base,st+24,"S_jRPG_Item_StaticData") && local_read<int32_t>(st+0x58)==298 &&
 picto_struct_field(base,st,"Item_HardcodedName_90_C7F763B74AAB28EF890A66854D7D95AA","NameProperty",0,8) &&
 picto_struct_field(base,st,"Item_Type_88_2F24F8FB4235429B4DE1399DBA533C78","ByteProperty",24,1) &&
 picto_struct_field(base,st,"Pictos_Data_103_EE44D66B4E4F16A7FD44FF9F25777CF4","ObjectProperty",192,8) &&
 picto_struct_field(base,st,"HideInInventory_105_28F500C94EA8D5C6632F7E8E4A85586E","BoolProperty",296,1);
}
#ifndef E33_PICTO_SCHEMA_FIXTURE
inline bool picto_owned_item(uint64_t base,uint64_t system,uint64_t id,uint64_t& item) {
 uint64_t d=0;const auto map=picto_field(base,system,"ItemInstances","MapProperty",576,80,&d);
 if(!map || (local_read<uint8_t>(d+0x98)&1))return false;
 const auto key=local_read<uint64_t>(d+0x70),value=local_read<uint64_t>(d+0x78);
 if(!key || !value || local_read<uint64_t>(key+16)!=d || local_read<uint64_t>(value+16)!=d ||
 !exact_name(base,local_read<uint64_t>(key+8),"NameProperty") || !exact_name(base,local_read<uint64_t>(value+8),"ObjectProperty") ||
 local_read<int32_t>(key+52)!=8 || local_read<int32_t>(value+52)!=8 || local_read<int32_t>(key+68)!=0 ||
 local_read<int32_t>(value+68)!=8 || local_read<int32_t>(d+0x80)!=8 || local_read<int32_t>(d+0x8c)!=24)return false;
 PictoSparseView view{};if(!picto_sparse(map,24,4096,view))return false;
 item=0;int found=0;
 for(int i=0;i<view.count;++i)if(view.active(i)) {
  const auto at=view.data+uint64_t(i)*24;if(local_read<uint64_t>(at)!=id)continue;
  ++found;item=local_read<uint64_t>(at+8);
 }
 if(found>1)return false;
 if(!found)return true;
 if(!call_capture(base,item).address || !picto_class(base,item,"BP_ItemInstance_Gear_Pictos_C","/Game/Gameplay/Pictos/BP_ItemInstance_Gear_Pictos"))return false;
 const auto quantity=picto_field(base,item,"Quantity","IntProperty",360,4),name=picto_field(base,item,"ItemDefinitionID","NameProperty",48,8);
 return quantity && name && local_read<int32_t>(quantity)==1 && local_read<uint64_t>(name)==id;
}
inline bool picto_legacy_owned(uint64_t base,uint64_t gi,uint64_t id,bool expected) {
 uint64_t d=0;auto array=picto_field(base,gi,"Inventory","ArrayProperty",856,16,&d);
 if(!array || (local_read<uint8_t>(d+0x70)&1))return false;
 const auto inner=local_read<uint64_t>(d+0x78),st=inner?local_read<uint64_t>(inner+0x70):0;
 if(!inner || local_read<uint64_t>(inner+16)!=d || !exact_name(base,local_read<uint64_t>(inner+8),"StructProperty") ||
 local_read<int32_t>(inner+52)!=312 || !st || !exact_name(base,st+24,"S_jRPG_Item_DynamicData") || local_read<int32_t>(st+0x58)!=312 ||
 !picto_struct_field(base,st,"StacksAmount_2_9F82380C4167D3E4C37234817EF904DC","IntProperty",0,4))return false;
 const auto sf=picto_struct_field(base,st,"ItemStaticData_9_59CF465348F5D7696BDFE68CB4071486","StructProperty",8,304);
 if(!sf || !picto_static_schema(base,local_read<uint64_t>(sf+0x70)))return false;
 const auto data=local_read<uint64_t>(array);const auto n=local_read<int32_t>(array+8),cap=local_read<int32_t>(array+12);
 if(n<0 || n>cap || cap>4096 || (n && (!data || (data&7))))return false;
 int found=0,quantity=0;
 for(int i=0;i<n;++i) {const auto at=data+uint64_t(i)*312;if(local_read<uint64_t>(at+8)==id){++found;quantity=local_read<int32_t>(at);}}
 return expected?(found==1 && quantity==1):(found==0);
}
inline bool picto_not_equipped(uint64_t base,uint64_t character,uint64_t id,uint64_t item) {
 for(int kind=0;kind<2;++kind) {
  uint64_t d=0;auto map=picto_field(base,character,kind?"EquipmentInstancePerSlot":"EquipmentPerSlot","MapProperty",kind?2112:56,80,&d);
  if(!map || (local_read<uint8_t>(d+0x98)&1))return false;
  const auto key=local_read<uint64_t>(d+0x70),value=local_read<uint64_t>(d+0x78);
  if(!key || !value || local_read<uint64_t>(key+16)!=d || local_read<uint64_t>(value+16)!=d ||
  !exact_name(base,local_read<uint64_t>(key+8),"StructProperty") || local_read<int32_t>(key+52)!=8 ||
  !exact_name(base,local_read<uint64_t>(key+0x70)+24,"FEquipmentSlot") ||
  !exact_name(base,local_read<uint64_t>(value+8),kind?"ObjectProperty":"StructProperty") ||
  local_read<int32_t>(value+52)!=(kind?8:304) || local_read<int32_t>(d+0x80)!=8 || local_read<int32_t>(value+68)!=8 ||
  (!kind && !picto_static_schema(base,local_read<uint64_t>(value+0x70))))return false;
  const auto stride=local_read<int32_t>(d+0x8c);
  if(stride!=(kind?24:320))return false;
  PictoSparseView view{};if(!picto_sparse(map,stride,128,view))return false;
  for(int i=0;i<view.count;++i)if(view.active(i) && local_read<uint64_t>(view.data+uint64_t(i)*stride+8)==(kind?item:id))return false;
 }
 return true;
}
inline void picto_inventory_dispatch(uint64_t dispatch,uint64_t target,uint64_t function,void* args,uint64_t flag,uint8_t saved_dispatch_flag) {
 __try {
  *reinterpret_cast<uint8_t*>(flag)=0;
  reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(dispatch)(reinterpret_cast<void*>(target),reinterpret_cast<void*>(function),args);
 } __finally {*reinterpret_cast<uint8_t*>(flag)=saved_dispatch_flag;}
}
inline void picto_inventory(uint64_t base,PictoProgressionPacket& p) {
 const auto manager=call_identity(base,p.target),fn=call_identity(base,p.function),asset=call_identity(base,p.source),
 table=call_identity(base,p.panel),gi=call_identity(base,p.game_instance);
 if(!manager || !fn || !asset || !table || !gi ||
 !picto_class(base,manager,"AC_jRPG_InventoryManager_C","/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_InventoryManager") ||
 !picto_class(base,asset,"BP_DataAsset_Item_Pictos_C","/Game/Gameplay/Inventory/BP_DataAsset_Item_Pictos") ||
 !picto_class(base,table,"CompositeDataTable","/Script/Engine") || !exact_name(base,table+24,"DT_jRPG_Items_Composite") ||
 !exact_name(base,local_read<uint64_t>(table+32)+24,"/Game/jRPGTemplate/Datatables/DT_jRPG_Items_Composite") ||
 !picto_class(base,gi,"BP_jRPG_GI_Custom_C","/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_GI_Custom") ||
 !picto_stable_script(base,fn,p.value?8:9) || !call_derives(base,local_read<uint64_t>(manager+16),local_read<uint64_t>(fn+32))) {p.error=1751;return;}
 uint64_t bd=0;
 const auto ref=picto_field(base,manager,"GameInstanceReference","ObjectProperty",184,8),
 flag=picto_field(base,manager,"ShouldDispatchModifications","BoolProperty",249,1,&bd),
 sysref=picto_field(base,gi,"InventorySystem","ObjectProperty",3296,8);
 if(!ref || local_read<uint64_t>(ref)!=gi || !flag || local_read<uint32_t>(bd+0x70)!=0xff010001 || local_read<uint8_t>(flag)>1 || !sysref){p.error=1752;return;}
 const auto system=local_read<uint64_t>(sysref);
 if(!call_capture(base,system).address || !picto_class(base,system,"BP_ItemUpgradeSystem_C","/Game/Gameplay/Pictos/BP_ItemUpgradeSystem") || !picto_static_schema(base,local_read<uint64_t>(table+40))){p.error=1753;return;}
 const uint8_t accessor[]={0x48,0x8d,0x41,0x30,0xc3};const auto getmap=local_read<uint64_t>(local_read<uint64_t>(table)+0x2d8);
 if(!getmap || std::memcmp(reinterpret_cast<void*>(getmap),accessor,sizeof(accessor))){p.error=1754;return;}
 PictoSparseView rows{};if(!picto_sparse(table+48,24,4096,rows)){p.error=1754;return;}
 uint64_t id=0;int matches=0;
 for(int i=0;i<rows.count;++i)if(rows.active(i)) {
  const auto at=rows.data+uint64_t(i)*24,row=local_read<uint64_t>(at+8);
  if(!row || (row&7)){p.error=1754;return;}
  if(local_read<uint64_t>(row+192)!=asset)continue;
  if(local_read<uint8_t>(row+24)!=2 || local_read<uint8_t>(row+296)!=0 || local_read<uint64_t>(row)!=local_read<uint64_t>(at)){p.error=1755;return;}
  ++matches;id=local_read<uint64_t>(at);
 }
 uint64_t item=0;
 if(matches!=1 || !id || !picto_owned_item(base,system,id,item) || bool(item)!=bool(p.expected) || !picto_legacy_owned(base,gi,id,p.expected!=0)){p.error=1756;return;}
 if(p.expected==p.value){p.observed=p.value;p.outcome=1;return;}
 if(!p.value && std::memcmp(reinterpret_cast<void*>(base+0x4abd100),picto_shipping_assert,sizeof(picto_shipping_assert))){p.error=1757;return;}
 // Audit every captured dependent Blueprint script and all loaded equipment.
 constexpr size_t count=sizeof(picto_scripts)/sizeof(PictoScriptShape);bool seen[count]{};unsigned characters=0;
 const auto objects=local_read<int32_t>(base+0x9361b84),chunks_count=local_read<int32_t>(base+0x9361b8c);const auto chunks=local_read<uint64_t>(base+0x9361b70);
 if(objects<=0 || objects>1000000 || chunks_count<=((objects-1)>>16) || chunks_count>32 || !chunks){p.error=1758;return;}
 for(int i=0;i<objects;++i) {
  const auto chunk=local_read<uint64_t>(chunks+uint64_t(i>>16)*8);if(!chunk){p.error=1758;return;}
  const auto obj=local_read<uint64_t>(chunk+uint64_t(i&65535)*24);if(!obj)continue;
  for(size_t s=11;s<count;++s) {
   const auto& shape=picto_objects[picto_scripts[s].object_id];
   if(!exact_name(base,obj+24,shape.chain[0].name))continue;
   if(picto_stable_script(base,obj,static_cast<uint32_t>(s)))seen[s]=true;
  }
  if(!p.value && !(local_read<uint32_t>(obj+8)&0x30) && picto_class(base,obj,"BP_CharacterData_C","/Game/Gameplay/CharacterData/BP_CharacterData")) {
   if(!call_capture(base,obj).address || !picto_not_equipped(base,obj,id,item)){p.error=1759;return;}
   ++characters;
  }
 }
 for(size_t s=11;s<count;++s)if(!seen[s]){p.error=1760;return;}
 if(!p.value && !characters){p.error=1759;return;}
 const auto dispatch=local_read<uint64_t>(local_read<uint64_t>(manager)+0x268);
 if(dispatch!=base+0x1393330 && dispatch!=base+0x332bb90){p.error=1761;return;}
 alignas(16) uint8_t args[4096]{};std::memcpy(args,&id,8);const int amount=1,encounter=-1;
 std::memcpy(args+8,&amount,4);if(p.value)std::memcpy(args+12,&encounter,4);
 p.outcome=2;const auto saved_dispatch_flag=local_read<uint8_t>(flag);
 picto_inventory_dispatch(dispatch,manager,fn,args,flag,saved_dispatch_flag);
 if(local_read<uint8_t>(flag)!=saved_dispatch_flag || !picto_owned_item(base,system,id,item) || bool(item)!=bool(p.value) || !picto_legacy_owned(base,gi,id,p.value!=0)){p.error=1762;return;}
 p.observed=p.value;p.outcome=1;
}

#endif // E33_PICTO_SCHEMA_FIXTURE
