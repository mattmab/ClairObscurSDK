#pragma once
#include "story_reward_extensions_packet.h"
#include "target_story_item_definitions.h"
#include "target_story_action.h"
namespace e33_story_rewards {
struct Dispatcher {
 uint64_t base=0,session=0,owner=0,leases[4]{};CallIdentity gi{},system{},function{},sources[2]{};
 uint32_t guid[4]{};uint64_t origins[2]{},extras[2][2]{},calls[2]{},grants[2]{};
 e33_story_items::Dispatcher*definitions=nullptr;DWORD thread=0;
 bool routing=false,unknown=false,dispatching=false;unsigned selected=2;uint64_t manager=0,frame_locals=0;int encounter=0;
 bool active()const{return owner||routing;}
 bool protects(uint64_t token)const{if(!active())return false;for(auto lease:leases)if(lease==token)return true;return false;}
 bool bound()const{e33_story_action::Dispatcher p;p.base=base;p.gi=gi;std::memcpy(p.guid,guid,16);return p.bound();}
 bool schema(uint64_t b,uint64_t f)const{
  if(!call_capture(b,f).address||!e33_mesh::named(b,local_read<uint64_t>(f+32),"AC_jRPG_InventoryManager_C","/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_InventoryManager")||
     !exact_name(b,f+24,"AddItemToInventory")||local_read<uint32_t>(f+0xb0)!=214040576U||local_read<uint16_t>(f+0xb6)!=24||
     local_read<uint16_t>(f+0xb8)!=65535||local_read<uint64_t>(f+0xd8)!=b+0x13937a0||!picto_stable_script(b,f,8))return false;
  const auto name=picto_struct_field(b,f,"ItemHardcodedName","NameProperty",0,8),amount=picto_struct_field(b,f,"Amount","IntProperty",8,4),loot=picto_struct_field(b,f,"LootContext","StructProperty",12,4),
   result=picto_struct_field(b,f,"GeneratedItem","ObjectProperty",16,8);
  return name&&amount&&loot&&result&&local_read<uint64_t>(name+0x38)==2251869606904468ULL&&local_read<uint64_t>(amount+0x38)==2251869606904468ULL&&
   local_read<uint64_t>(loot+0x38)==2251869606903956ULL&&local_read<uint64_t>(result+0x38)==2251868533162880ULL;
 }
 uint64_t begin(uint64_t f,void*object,void*frame){
  if(unknown||dispatching||selected<2||thread!=GetCurrentThreadId()||f!=function.address||!call_identity(base,function)||!bound()||!definitions||!definitions->current()||!call_identity(base,system))return 0;
  const auto recipient=reinterpret_cast<uint64_t>(object),stack=reinterpret_cast<uint64_t>(frame);
  if(!call_capture(base,recipient).address||!picto_class(base,recipient,"AC_jRPG_InventoryManager_C","/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_InventoryManager")||
     zone_ref(base,recipient,"GameInstanceReference")!=gi.address||!stack||local_read<uint64_t>(stack+0x10)!=f||local_read<uint64_t>(stack+0x90)||
     local_read<uint64_t>(stack+0x18)!=recipient||local_read<uint64_t>(stack+0x20)!=local_read<uint64_t>(f+0x60))return 0;
  const auto locals=local_read<uint64_t>(stack+0x28);if(!locals||local_read<int32_t>(locals+8)!=1)return 0;
  e33_dialogue_text::Dispatcher helper;
  const auto dialogue=helper.object_field(base,system.address,"ActiveDialogue"),world=helper.world(base,system.address);
  if(!dialogue||!world||helper.world(base,dialogue)!=world||zone_ref(base,world,"OwningGameInstance")!=gi.address)return 0;
  const auto cls=local_read<uint64_t>(dialogue+16),name=local_read<uint64_t>(locals);
  for(unsigned i=0;i<2;++i)if(call_identity(base,sources[i])&&cls==sources[i].address&&name==origins[i]){
   for(unsigned j=0;j<(i?1U:2U);++j)if(!definitions->definition(extras[i][j]))return 0;
   selected=i;manager=recipient;frame_locals=locals;encounter=local_read<int32_t>(locals+12);return owner;
  }return 0;
 }
 void end(uint64_t token){
  if(token!=owner||selected>1||thread!=GetCurrentThreadId()||!bound()||!definitions||!definitions->current()){
   unknown=true;return;}
  const auto profile=selected;
  if(local_read<uint64_t>(frame_locals)!=origins[profile]||local_read<int32_t>(frame_locals+8)!=1||!picto_legacy_owned(base,gi.address,origins[profile],true)){
   unknown=true;return;}
  ++calls[profile];dispatching=true;unknown=true;
  const auto dispatch=local_read<uint64_t>(local_read<uint64_t>(manager)+0x268);
  if(dispatch!=base+0x1393330&&dispatch!=base+0x332bb90)return;
  for(unsigned i=0;i<(profile?1U:2U);++i){
   alignas(16)uint8_t args[32]{};std::memcpy(args,&extras[profile][i],8);const int amount=1;
   std::memcpy(args+8,&amount,4);std::memcpy(args+12,&encounter,4);
   // ProcessEvent invokes the original function entry. It does not re-enter
   // the opcode argument transform for this top-level extension dispatch.
   reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(dispatch)(reinterpret_cast<void*>(manager),reinterpret_cast<void*>(function.address),args);
   if(!picto_legacy_owned(base,gi.address,extras[profile][i],true))return;
   ++grants[profile];
  }
  unknown=false;dispatching=false;selected=2;manager=frame_locals=0;
 }
 static e33_blueprint_transform::Decision pre(void*context,uint64_t f,void*object,void*frame){
  __try{return {static_cast<Dispatcher*>(context)->begin(f,object,frame),false};}
  __except(EXCEPTION_EXECUTE_HANDLER){static_cast<Dispatcher*>(context)->unknown=true;return {};}
 }
 static void post(void*context,uint64_t token){
  __try{static_cast<Dispatcher*>(context)->end(token);}
  __except(EXCEPTION_EXECUTE_HANDLER){static_cast<Dispatcher*>(context)->unknown=true;}
 }
 bool close(){
  if(unknown||dispatching||selected<2)return false;
  if(routing){if(!e33_blueprint_transform::detach(this)||!BlueprintDirectTrace::release_narrative(function.address))return false;routing=false;}
  if(definitions&&owner){if(!definitions->consumers)return false;--definitions->consumers;}
  definitions=nullptr;owner=0;return true;
 }
 template<class Pool>void run(uint64_t b,uint64_t s,Pool&pool,Packet&p,e33_story_items::Dispatcher&items){
  if(!valid(p)||unknown){p.error=unknown?uncertain:rejected;return;}
  if(p.mode){
   if(owner!=p.owner||session!=s||std::memcmp(&gi,&p.gi,16)||std::memcmp(&system,&p.system,16)||std::memcmp(&function,&p.function,16)||std::memcmp(guid,p.guid,16)||!definitions||definitions->owner!=p.definitions_owner){p.error=rejected;return;}
   if(p.mode==2){p.state=close()?3U:0U;if(!p.state)p.error=uncertain;return;}
   std::memcpy(p.calls,calls,sizeof(calls));std::memcpy(p.grants,grants,sizeof(grants));p.state=2;return;
  }
  const CallIdentity ids[]={p.gi,p.function,p.flower_class,p.jules_class};
  for(unsigned i=0;i<4;++i)if(!call_identity(b,ids[i])||!pool.owns_object(s,p.leases[i],ids[i].address)){p.error=rejected;return;}
  if(active()||items.owner!=p.definitions_owner||!items.current()||!call_identity(b,p.system)||!schema(b,p.function.address)||
     !e33_mesh::named(b,p.flower_class.address,"BP_Dialogue_Gardens_GustaveFlower_C","/Game/Narrative/Dialogs/LevelsDialogs/Lumiere/WalkAct1/BP_Dialogue_Gardens_GustaveFlower")||
     !e33_mesh::named(b,p.jules_class.address,"BP_Dialogue_Jules_C","/Game/Narrative/Dialogs/LevelsDialogs/Lumiere/WalkAct1/BP_Dialogue_Jules")){p.error=rejected;return;}
  uint64_t origin_names[2]{},extra_names[2][2]{};
  for(unsigned i=0;i<2;++i){if(!e33_blueprint_names::resolve(b,p.origins[i],origin_names[i])){p.error=rejected;return;}
   for(unsigned j=0;j<(i?1U:2U);++j)if(!e33_blueprint_names::resolve(b,p.extras[i][j],extra_names[i][j])||!items.definition(extra_names[i][j])){p.error=rejected;return;}}
  base=b;session=s;owner=p.owner;gi=p.gi;system=p.system;function=p.function;sources[0]=p.flower_class;sources[1]=p.jules_class;
  std::memcpy(leases,p.leases,sizeof(leases));std::memcpy(guid,p.guid,16);std::memcpy(origins,origin_names,sizeof(origins));std::memcpy(extras,extra_names,sizeof(extras));
  definitions=&items;thread=GetCurrentThreadId();std::memset(calls,0,sizeof(calls));std::memset(grants,0,sizeof(grants));
  if(!bound()||!e33_blueprint_transform::attach(this,function.address,pre,post)){owner=0;definitions=nullptr;p.error=rejected;return;}
  if(!BlueprintDirectTrace::retain_narrative(b,function.address)){e33_blueprint_transform::detach(this);owner=0;definitions=nullptr;p.error=rejected;return;}
  ++items.consumers;routing=true;p.state=1;
 }
};
}
