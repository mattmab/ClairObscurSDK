#pragma once
#include "zone_travel_protocol.h"
#include "zone_display_name.h"
// Included after the reflected identity and read-only sparse-table helpers.
inline bool zone_named(uint64_t base,uint64_t object,const char* name,const char* package) {
 if(!call_capture(base,object).address || !exact_name(base,object+24,name))return false;
 const auto outer=local_read<uint64_t>(object+32);
 return call_capture(base,outer).address && exact_name(base,outer+24,package);
}
inline uint64_t zone_ref(uint64_t base,uint64_t object,const char* name) {
 if(!call_capture(base,object).address)return 0;
 auto cls=local_read<uint64_t>(object+16);
 for(unsigned zone_depth=0;cls && zone_depth<32;++zone_depth,cls=local_read<uint64_t>(cls+0x40)) {
  unsigned walked=0;
  for(auto f=local_read<uint64_t>(cls+0x50);f && ++walked<512;f=local_read<uint64_t>(f+24)) {
   if(!exact_name(base,f+32,name))continue;
   const auto offset=local_read<int32_t>(f+0x44);
   if(local_read<uint64_t>(f+16)!=(cls|1) || local_read<uint64_t>(f)!=base+0x6e11d38 || local_read<uint32_t>(f+48)!=1 || local_read<uint32_t>(f+52)!=8 || offset<40 || offset+8>local_read<int32_t>(cls+0x58))return 0;
   return local_read<uint64_t>(object+offset);
  }
 }
 return 0;
}
inline void zone_travel(uint64_t base,ZoneTravelPacket& p) {
 if(!zone_packet_valid(p)){p.error=1800;return;}
 const auto table=call_identity(base,p.table),fn=call_identity(base,p.function),cdo=call_identity(base,p.target),gi=call_identity(base,p.gi),player=call_identity(base,p.player),pc=call_identity(base,p.controller);
 if(!table||!fn||!cdo||!gi||!player||!pc){p.error=1801;return;}
 const char* lib="/Game/jRPGTemplate/Blueprints/Basics/FL_jRPG_CustomFunctionLibrary";
 const auto owner=local_read<uint64_t>(fn+32);
 if(!zone_named(base,owner,"FL_jRPG_CustomFunctionLibrary_C",lib) || local_read<uint64_t>(cdo+16)!=owner || !zone_named(base,cdo,"Default__FL_jRPG_CustomFunctionLibrary_C",lib) || !(local_read<uint32_t>(cdo+8)&0x10) || !exact_name(base,fn+24,"ChangeMapByName") || !zone_named(base,local_read<uint64_t>(fn+16),"Function","/Script/CoreUObject")){p.error=1802;return;}
 if(local_read<uint32_t>(fn+0xb0)!=0xc822000 || local_read<uint16_t>(fn+0xb6)!=24 || local_read<uint16_t>(fn+0xb8)!=65535 || local_read<uint32_t>(fn+0x58)!=584 || local_read<uint64_t>(fn+0xd8)!=base+0x13937a0){p.error=1803;return;}
 const char* names[]={"LevelDestination","SpawnPointTag","__WorldContext"};
 const uint64_t tables[]={0x6e13040,0x6e136a0,0x6e11d38};
 const uint64_t flags[]={0x8001040000296ULL,0x8001000000094ULL,0x8001000000294ULL};
 auto f=local_read<uint64_t>(fn+0x50);
 for(unsigned i=0;i<3;++i) {
  if(!f || local_read<uint64_t>(f)!=base+tables[i] || local_read<uint64_t>(f+16)!=(fn|1) || !exact_name(base,f+32,names[i]) || local_read<uint32_t>(f+48)!=1 || local_read<uint32_t>(f+52)!=8 || local_read<uint64_t>(f+56)!=flags[i] || local_read<uint32_t>(f+68)!=i*8){p.error=1804;return;}
  if(i==1 && !zone_named(base,local_read<uint64_t>(f+0x70),"GameplayTag","/Script/GameplayTags")){p.error=1804;return;}
  if(i==2 && !zone_named(base,local_read<uint64_t>(f+0x70),"Object","/Script/CoreUObject")){p.error=1804;return;}
  f=local_read<uint64_t>(f+24);
 }
 unsigned locals=0;for(;f && ++locals<32;f=local_read<uint64_t>(f+24))if(local_read<uint64_t>(f+56)&0x80){p.error=1804;return;}
 if(f || locals!=6){p.error=1804;return;}
 if(!zone_named(base,local_read<uint64_t>(gi+16),"BP_jRPG_GI_Custom_C","/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_GI_Custom") || !zone_named(base,local_read<uint64_t>(player+16),"LocalPlayer","/Script/Engine") || zone_ref(base,player,"PlayerController")!=pc){p.error=1805;return;}
 auto world=local_read<uint64_t>(pc+32);unsigned zone_depth=0;
 while(world && ++zone_depth<8 && !exact_name(base,local_read<uint64_t>(world+16)+24,"World"))world=local_read<uint64_t>(world+32);
 if(!world || zone_depth>=8 || zone_ref(base,world,"OwningGameInstance")!=gi || (local_read<uint32_t>(pc+8)&0x40000030)){p.error=1805;return;}
 const auto changing=picto_field(base,gi,"IsChangingMap","BoolProperty",464,1),loaded=picto_field(base,gi,"SaveLoaded","BoolProperty",2680,1);
 if(!changing||!loaded||local_read<uint8_t>(changing)||!local_read<uint8_t>(loaded)){p.error=1806;return;}
 if(!zone_named(base,table,"DT_LevelData","/Game/Gameplay/LevelData/DT_LevelData") || !zone_named(base,local_read<uint64_t>(table+16),"DataTable","/Script/Engine")){p.error=1807;return;}
 const auto accessor=local_read<uint64_t>(local_read<uint64_t>(table)+0x2d8);
 const uint8_t expected[]={0x48,0x8d,0x41,0x30,0xc3};
 if(accessor<base || accessor>=base+166776832 || std::memcmp(reinterpret_cast<void*>(accessor),expected,5)){p.error=1807;return;}
 const auto st=local_read<uint64_t>(table+40);
 if(!zone_named(base,st,"FLevelDataEntry","/Game/Gameplay/LevelData/FLevelDataEntry") || local_read<uint32_t>(st+0x58)!=432 || !picto_struct_field(base,st,"LevelAssetName_85_BF09694C41CC0444295731A40341A5F9","NameProperty",0,8) || !picto_struct_field(base,st,"MainSpawnPoint_72_5C7B345E44E5B2867FCE0687BB65019F","StructProperty",152,8)){p.error=1808;return;}
 PictoSparseView view{};if(!picto_sparse(table+48,24,4096,view)){p.error=1809;return;}
 uint64_t key=0,tag=0;unsigned found=0;
 for(int i=0;i<view.count;++i)if(view.active(i)) {
  const auto at=view.data+uint64_t(i)*24;if(!zone_display_name(base,at,p.level))continue;
  const auto row=local_read<uint64_t>(at+8);
  if(!row || (row&7) || !zone_display_name(base,row,p.asset) || !zone_display_name(base,row+152,p.tag) || exact_name(base,row+152,"None")){p.error=1810;return;}
  key=local_read<uint64_t>(at);tag=local_read<uint64_t>(row+152);++found;
 }
 if(found!=1){p.error=1810;return;}
 const auto dispatch=local_read<uint64_t>(local_read<uint64_t>(cdo)+0x268);
 if(dispatch!=base+0x1393330 && dispatch!=base+0x332bb90){p.error=1811;return;}
 // Resolve the current game's pause widget; its Resume callback broadcasts
 // OnBackToExploration, which restores both pause and game input state.
 const auto pause=zone_ref(base,pc,"PauseMenuWidget");
 const auto pause_class=pause?local_read<uint64_t>(pause+16):0;
 if(!call_capture(base,pause).address || !zone_named(base,pause_class,"WBP_PauseMenu_C","/Game/UI/Widgets/InGame_Menu/PauseMenu/WBP_PauseMenu")){p.error=1813;return;}
 const auto active=picto_field(base,pause,"bIsActive","BoolProperty",872,1);
 uint64_t resume=0;unsigned functions=0;
 for(auto child=local_read<uint64_t>(pause_class+0x48);child && ++functions<256;child=local_read<uint64_t>(child+0x28)) {
  if(!call_capture(base,child).address){p.error=1813;return;}
  if(exact_name(base,child+24,"OnResumeClicked")){resume=child;break;}
 }
 if(!active || !resume || local_read<uint64_t>(resume+32)!=pause_class || !zone_named(base,local_read<uint64_t>(resume+16),"Function","/Script/CoreUObject") || local_read<uint32_t>(resume+0xb0)!=0xc020000 || local_read<uint16_t>(resume+0xb6)!=0 || local_read<uint16_t>(resume+0xb8)!=65535 || local_read<uint32_t>(resume+0x58)!=0 || local_read<uint64_t>(resume+0x50)!=0 || local_read<uint64_t>(resume+0xd8)!=base+0x13937a0){p.error=1813;return;}
 const auto resume_dispatch=local_read<uint64_t>(local_read<uint64_t>(pause)+0x268);
 if(resume_dispatch!=base+0x1393330 && resume_dispatch!=base+0x332bb90){p.error=1813;return;}
 if(!p.operation){p.outcome=1;return;}
 if(local_read<uint8_t>(active)) {
  p.outcome=2;
  reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(resume_dispatch)(reinterpret_cast<void*>(pause),reinterpret_cast<void*>(resume),nullptr);
  if(local_read<uint8_t>(active) || call_identity(base,p.controller)!=pc || zone_ref(base,player,"PlayerController")!=pc){p.error=1814;return;}
 }

 // Copy only existing, table-validated FNames. No constructors, allocations,
 // caller pointers, raw GI writes, or post-load recovery are involved.
 alignas(16) uint64_t args[3]={key,tag,gi};p.outcome=2;
 reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(dispatch)(reinterpret_cast<void*>(cdo),reinterpret_cast<void*>(fn),args);
 p.outcome=1;
}
