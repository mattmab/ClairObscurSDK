#pragma once
#include "story_inworld_frame.h"
#include "blueprint_direct_trace.h"
#include "blueprint_name_resolution.h"
#include "retired_world_target.h"
#include "owned_action_array_copy.h"
namespace e33_story_inworld {
struct Dispatcher {
 Frame frame;uint64_t base=0,session=0,owner=0,ticket=0,widget_token=0;
 CallIdentity asset{},system{},world{},widget{},finished{},widget_interrupt{},query{},interrupt{};
 uint64_t asset_lease=0,system_lease=0;size_t hooks[2]{};bool routing=false,normal_finished=false,interrupted=false,seen_playing=false;
 uint32_t terminal=0;DWORD thread=0;
 TargetStringValue owned_array{};
 bool empty()const{return !frame.prepared&&!frame.attached&&!frame.unknown&&!hooks[0]&&!hooks[1]&&!routing&&!widget_token;}
 bool active()const{return !empty();}
 bool protects(uint64_t token)const{return active()&&token&&(token==asset_lease||token==system_lease||token==widget_token);}
 bool function(uint64_t b,uint64_t f,const char* cls,const char* package,const char* name,uint32_t flags,uint16_t size)const{
  return call_capture(b,f).address&&e33_mesh::named(b,local_read<uint64_t>(f+32),cls,package)&&exact_name(b,f+24,name)&&
   local_read<uint32_t>(f+0xb0)==flags&&local_read<uint16_t>(f+0xb6)==size&&local_read<uint16_t>(f+0xb8)==65535&&
   local_read<uint64_t>(f+0xd8)==b+0x13937a0&&local_read<int32_t>(f+0x68)>0;
 }
 bool parameters(uint64_t b,uint64_t f,const char* input,const char* output)const{
  unsigned n=0,steps=0;for(auto field=local_read<uint64_t>(f+0x50);field&&steps++<128;field=local_read<uint64_t>(field+24)){
   if(!(local_read<uint64_t>(field+0x38)&128))continue;
   if(n>1||local_read<uint64_t>(field+16)!=(f|1)||local_read<int32_t>(field+0x30)!=1)return false;
   if(!n){if(!exact_name(b,field+32,input)||!exact_name(b,local_read<uint64_t>(field+8),"ObjectProperty")||
      local_read<int32_t>(field+0x44)!=0||local_read<int32_t>(field+0x34)!=8||local_read<uint64_t>(field+0x38)!=0x8001000000294ULL||
      !e33_mesh::named(b,local_read<uint64_t>(field+0x70),"BP_DA_IWD_data_C","/Game/Dialogues/Data/BP_DA_IWD_data"))return false;
   }else if(!exact_name(b,field+32,output)||!exact_name(b,local_read<uint64_t>(field+8),"BoolProperty")||
      local_read<int32_t>(field+0x44)!=8||local_read<int32_t>(field+0x34)!=1||local_read<uint64_t>(field+0x38)!=0x8001040000380ULL||local_read<uint32_t>(field+0x70)!=0xff010001U)return false;
   ++n;
  }return n==2&&steps<128;
 }
 uint64_t lines_slot(uint64_t b,uint64_t object,uint64_t*property=nullptr)const{
  uint64_t field=0;const auto slot=picto_field(b,object,"Lines","ArrayProperty",48,16,&field);
  const auto inner=slot?local_read<uint64_t>(field+0x78):0,st=inner?local_read<uint64_t>(inner+0x70):0;
  if(!slot||!inner||local_read<uint64_t>(inner+16)!=field||!exact_name(b,local_read<uint64_t>(inner+8),"StructProperty")||
     local_read<int32_t>(inner+0x30)!=1||local_read<int32_t>(inner+0x34)!=88||
     !e33_mesh::named(b,st,"S_DialogueLine","/Game/LevelTools/MovementZone/S_DialogueLine")||local_read<int32_t>(st+0x58)!=88)return 0;
  const char* names[]={"Character_21_9CCAA85F4D431E9DD912FD9CB38DFBB9","Emotion_22_4E5F2363442944395D427CBC0DCCAFFD",
   "DelayToDelete_12_F7B8F4424E025AE635FD8BA9513B8507","DelayToAnswer_14_1F1CDEEA43E0BEF54D3810A237AA242C","UseSoundDuration_30_2BFE9A814C5DA24658A59C8CB417A17F",
   "DialogWave_25_CFDA519F4908618047A8D295B783A40F","PortraitOnTheRight_32_A078243C417EE058757087B38EE1B018","SoundEventRow_35_4369BC3D47B0C2E3C9C07A9E49CF92E7",
   "LineText_41_AD35B4F044D43FEB5B62D58635EAC75F","LineSound_44_C57AC45742D2E25B6D1951AFEDB7085C"};
  const char* types[]={"ByteProperty","ByteProperty","DoubleProperty","DoubleProperty","BoolProperty","ObjectProperty","BoolProperty","StructProperty","TextProperty","ObjectProperty"};
  const int offsets[]={0,1,8,16,24,32,40,48,64,80},widths[]={1,1,8,8,1,8,1,16,16,8};
  for(unsigned i=0;i<10;++i){const auto f=picto_struct_field(b,st,names[i],types[i],offsets[i],widths[i]);
   if(!f||((i==4||i==6)&&local_read<uint32_t>(f+0x70)!=0xff010001U))return 0;
   if(i==7){const auto h=local_read<uint64_t>(f+0x70);
    if(!e33_mesh::named(b,h,"DataTableRowHandle","/Script/Engine")||local_read<int32_t>(h+0x58)!=16||
      !picto_struct_field(b,h,"DataTable","ObjectProperty",0,8)||!picto_struct_field(b,h,"RowName","NameProperty",8,8))return 0;}
  }if(property)*property=field;return slot;
 }
 bool copy_lines(uint64_t b,uint64_t object,const TargetStringValue& source,TargetStringValue& result)const{
  uint64_t property=0;const auto slot=lines_slot(b,object,&property);
  if(!slot||!property||local_read<uint64_t>(property)!=b+e33_action_clone::array_property_table||
     (local_read<uint8_t>(property+0x70)&1)||
     local_read<uint64_t>(b+e33_action_clone::array_property_table+0xf0)!=b+e33_action_clone::array_copy_entry||
     std::memcmp(reinterpret_cast<void*>(b+e33_action_clone::array_copy_entry),e33_action_clone::array_copy_prefix,sizeof(e33_action_clone::array_copy_prefix)))return false;
  // This qualified property performs the allocator and nested FText copies.
  // The source remains a borrowed staging view only for this synchronous call.
  using Copy=void(*)(void*,void*,const void*,int);
  reinterpret_cast<Copy>(b+e33_action_clone::array_copy_entry)(reinterpret_cast<void*>(property),reinterpret_cast<void*>(slot),&source,1);
  result=local_read<TargetStringValue>(slot);return true;
 }
 bool object_kind(uint64_t b,const CallIdentity& id,const char* cls,const char* package)const{
  if(zero_identity(id))return true;
  auto o=call_identity(b,id);if(!o||(local_read<uint32_t>(o+8)&0x40018030U))return false;
  for(auto c=local_read<uint64_t>(o+16),n=uint64_t(0);c&&n++<32;c=local_read<uint64_t>(c+0x40))if(e33_mesh::named(b,c,cls,package))return true;
  return false;
 }
 void observe(void* object,bool interrupt_event){
  if(!frame.attached||frame.unknown||thread!=GetCurrentThreadId()||reinterpret_cast<uint64_t>(object)!=widget.address||
     !call_identity(base,widget)||!call_identity(base,asset))return;
  uint64_t field=0;
  if(!picto_field(base,widget.address,"InWorldDialogue","ObjectProperty",848,8,&field)||local_read<uint64_t>(widget.address+848)!=asset.address)return;
  // The retained, uniquely bound widget identifies the exact private playback.
  if(interrupt_event)interrupted=true;else normal_finished=true;
 }
 static void complete_callback(void* context,void* object,void*,void*){
  __try{static_cast<Dispatcher*>(context)->observe(object,false);}__except(EXCEPTION_EXECUTE_HANDLER){static_cast<Dispatcher*>(context)->frame.unknown=true;}
 }
 static void interrupt_callback(void* context,void* object,void*,void*){
  __try{static_cast<Dispatcher*>(context)->observe(object,true);}__except(EXCEPTION_EXECUTE_HANDLER){static_cast<Dispatcher*>(context)->frame.unknown=true;}
 }
 bool query_playing(uint64_t b,uint64_t f,e33_dialogue_text::Dispatcher& helper,bool& playing){
  const auto object=call_identity(b,system);
  if(!object||!function(b,f,"BP_DialogueSystemComponent_C","/Game/Gameplay/DialogueSystem/BP_DialogueSystemComponent","IsPlayingSpecificInWorldDialogue",0x1c420000,9)||!parameters(b,f,"InWorldDialogue","IsPlaying"))return false;
  const auto dispatch=local_read<uint64_t>(local_read<uint64_t>(object)+0x268);
  if(dispatch!=b+0x1393330&&dispatch!=b+0x332bb90)return false;
  alignas(8)uint8_t args[16]{};std::memcpy(args,&asset.address,8);
  reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(dispatch)(reinterpret_cast<void*>(object),reinterpret_cast<void*>(f),args);
  if(args[8]>1||std::memcmp(args,&asset.address,8)||helper.world(b,object)!=world.address)return false;
  playing=args[8]!=0;return true;
 }
 template<class Pool> bool detach(uint64_t b,uint64_t s,Pool& pool,bool world_retired=false){
  if(frame.unknown)return false;
  if(frame.attached){
   if(!pool.owns_retirement_storage(s,asset_lease,asset.address))return false;
   const auto live_asset=call_identity(b,asset);
   if(!live_asset||(local_read<uint32_t>(live_asset+8)&0x40018030U)){
    // Forced purge may already have destroyed this world-owned data asset.
    // Its engine allocation is then the engine's responsibility; never touch
    // a dead/reused UObject or free that allocation a second time.
    if(!world_retired||!independent_line_array(owned_array,frame.array))return false;
   }else{
    const auto slot=lines_slot(b,live_asset);
    if(!slot){frame.unknown=true;return false;}
    const auto current=local_read<TargetStringValue>(slot);const TargetStringValue empty{};
    if(world_retired&&!std::memcmp(&current,&empty,sizeof(empty))){/* already cleared by the engine */}
    else{
     if(std::memcmp(&current,&owned_array,sizeof(current))||!independent_line_array(owned_array,frame.array)){frame.unknown=true;return false;}
     TargetStringValue cleared{};
     if(!copy_lines(b,live_asset,empty,cleared)||cleared.count){frame.unknown=true;return false;}
    }
   }
   owned_array={};frame.attached=false;
  }
  for(auto& hook:hooks)if(hook){if(!e33_trace::TraceSlots<>::remove(hook))return false;hook=0;}
  if(routing){if(!BlueprintDirectTrace::release_inworld())return false;routing=false;}
  TargetOwnedTextOps ops{b};if(!frame.cleanup(ops))return false;
  if(widget_token){TargetStrongReferenceOps release{b,widget};if(pool.release(release,s,widget_token)!=StrongLeaseResult::Ok)return false;widget_token=0;}
  owner=0;ticket=0;return true;
 }
 template<class Pool> void run(uint64_t b,uint64_t s,Pool& pool,Packet& p,e33_dialogue_text::Dispatcher& helper){
  if(!valid(p)||!TargetPodSchemaOps{b}.context()||frame.unknown){p.error=frame.unknown?uncertain:rejected;return;}
  if(p.mode){
   if(owner!=p.owner||ticket!=p.ticket||session!=s||thread!=GetCurrentThreadId()||
      std::memcmp(&asset,&p.asset,sizeof(asset))||std::memcmp(&system,&p.system,sizeof(system))||std::memcmp(&query,&p.query,sizeof(query))||std::memcmp(&interrupt,&p.interrupt,sizeof(interrupt))||asset_lease!=p.asset_lease||system_lease!=p.system_lease){p.error=rejected;return;}
   if(p.mode==4){e33_retired_world::TargetOps ops{b};
    if(e33_retired_world::double_observe(ops,world)!=e33_retired_world::Result::Retired){p.error=rejected;return;}
    p.state=detach(b,s,pool,true)?5:0;if(!p.state)p.error=uncertain;return;}
   if(p.mode==2&&!frame.attached){p.state=detach(b,s,pool)?5:0;if(!p.state)p.error=uncertain;return;}
   if(terminal==3){p.state=p.mode==2?(detach(b,s,pool)?3U:0U):3U;if(!p.state)p.error=uncertain;return;}
   e33_retired_world::TargetOps current_ops{b};e33_retired_world::Snapshot now{};
   if(!current_ops.observe(now)||!e33_retired_world::same(now.world,world)){p.error=rejected;return;}
   bool playing=false;if(!call_identity(b,query)||!query_playing(b,p.query.address,helper,playing)){p.error=uncertain;frame.unknown=true;return;}
   if(playing)seen_playing=true;
   if(p.mode==3&&playing){
    if(!call_identity(b,interrupt)||!function(b,p.interrupt.address,"BP_DialogueSystemComponent_C","/Game/Gameplay/DialogueSystem/BP_DialogueSystemComponent","InterruptInWorldDialogue",0xc020000,0)){p.error=rejected;return;}
    interrupted=true;const auto dispatch=local_read<uint64_t>(local_read<uint64_t>(system.address)+0x268);
    reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(dispatch)(reinterpret_cast<void*>(system.address),reinterpret_cast<void*>(p.interrupt.address),nullptr);
    if(!query_playing(b,p.query.address,helper,playing)){p.error=uncertain;frame.unknown=true;return;}
   }
   if(!playing){
    if(interrupted)terminal=4;
    else if(normal_finished&&seen_playing)terminal=2;
    else{p.error=uncertain;frame.unknown=true;return;}
   }
   if(p.mode==2){if(playing){p.error=pending;return;}p.state=terminal;if(!detach(b,s,pool)){p.state=0;p.error=uncertain;}return;}
   p.state=playing?1:terminal;return;
  }
  if(!empty()){p.error=pending;return;}
  for(const auto& id:{p.play,p.query,p.interrupt,p.finished,p.widget_interrupt})if(!call_identity(b,id)){p.error=rejected;return;}
  const auto a=call_identity(b,p.asset),sys=call_identity(b,p.system),carrier=call_identity(b,p.carrier);
  if(!a||!sys||!carrier||!pool.owns_object(s,p.asset_lease,a)||!pool.owns_object(s,p.system_lease,sys)||
     local_read<uint64_t>(a+32)!=carrier||(local_read<uint32_t>(a+8)&0x40000030U)||
     !e33_mesh::named(b,local_read<uint64_t>(a+16),"BP_DA_IWD_data_C","/Game/Dialogues/Data/BP_DA_IWD_data")||
     !e33_mesh::named(b,local_read<uint64_t>(sys+16),"BP_DialogueSystemComponent_C","/Game/Gameplay/DialogueSystem/BP_DialogueSystemComponent")){p.error=rejected;return;}
  const auto controller=local_read<uint64_t>(sys+32),player=helper.object_field(b,controller,"Player"),w=helper.world(b,controller);
  if(!player||!e33_mesh::named(b,local_read<uint64_t>(player+16),"LocalPlayer","/Script/Engine")||helper.object_field(b,player,"PlayerController")!=controller||!w||helper.world(b,carrier)!=w){p.error=rejected;return;}
  const auto slot=lines_slot(b,a);const auto prior_header=slot?local_read<TargetStringValue>(slot):TargetStringValue{};
  if(!slot||prior_header.data||prior_header.count||prior_header.capacity||
     !function(b,p.play.address,"BP_DialogueSystemComponent_C","/Game/Gameplay/DialogueSystem/BP_DialogueSystemComponent","PlayInWorldDialogue",0xc420000,9)||!parameters(b,p.play.address,"DialogToPlay","DialogueNotPlayed")||
     !function(b,p.finished.address,"WBP_DialogNotifBox_C","/Game/UI/Widgets/HUD_Exploration/WBP_DialogNotifBox","OnAllDialogueLinesFinished",0xc040000,1)||
     !function(b,p.widget_interrupt.address,"WBP_DialogNotifBox_C","/Game/UI/Widgets/HUD_Exploration/WBP_DialogNotifBox","InterruptDialog",0xc020000,0)){p.error=rejected;return;}
  uint64_t names[capacity]{};
  for(uint32_t i=0;i<p.count;++i){const auto& line=p.lines[i];
   if(!object_kind(b,line.wave,"DialogueWave","/Script/Engine")||!object_kind(b,line.sound,"SoundBase","/Script/Engine")||!object_kind(b,line.table,"DataTable","/Script/Engine")||
      (line.row[0]&&std::strcmp(line.row,"None")&&!e33_blueprint_names::resolve(b,line.row,names[i]))){p.error=rejected;return;}
  }
  const auto existing_widget=helper.object_field(b,sys,"CurrentInWorldDialogueWidget");
  if(existing_widget&&helper.object_field(b,existing_widget,"InWorldDialogue")){p.error=pending;return;}
  const auto dispatch=local_read<uint64_t>(local_read<uint64_t>(sys)+0x268);
  if(dispatch!=b+0x1393330&&dispatch!=b+0x332bb90){p.error=rejected;return;}
  base=b;session=s;owner=p.owner;ticket=p.ticket;asset=p.asset;system=p.system;world=call_capture(b,w);widget={};thread=GetCurrentThreadId();asset_lease=p.asset_lease;system_lease=p.system_lease;
  finished=p.finished;widget_interrupt=p.widget_interrupt;query=p.query;interrupt=p.interrupt;normal_finished=false;interrupted=false;seen_playing=false;terminal=0;
  TargetOwnedTextOps ops{b};if(!frame.prepare(ops,p)){p.error=uncertain;return;}
  for(uint32_t i=0;i<p.count;++i)frame.lines[i].row=names[i];
  if(!BlueprintDirectTrace::retain_inworld(b,p.finished.address,p.widget_interrupt.address)){p.error=uncertain;return;}routing=true;
  // Both source calls use EX_LocalFinalFunction (0x45), whose shared route
  // executes the interpreter directly. POST delivery therefore requires an
  // observation-only slot; replacing UFunction::Func alone misses that path.
  hooks[0]=e33_trace::TraceSlots<>::install(reinterpret_cast<void* volatile*>(p.finished.address+0xd8),reinterpret_cast<e33_trace::Entry>(b+0x13937a0),complete_callback,this,false,false);
  hooks[1]=e33_trace::TraceSlots<>::install(reinterpret_cast<void* volatile*>(p.widget_interrupt.address+0xd8),reinterpret_cast<e33_trace::Entry>(b+0x13937a0),interrupt_callback,this,true,false);
  if(!hooks[0]||!hooks[1]){p.error=uncertain;return;}
  frame.attached=true;
  if(!copy_lines(b,a,frame.array,owned_array)||!independent_line_array(owned_array,frame.array)){
   frame.unknown=true;p.error=uncertain;return;
  }
  alignas(8)uint8_t args[16]{};std::memcpy(args,&a,8);
  reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(dispatch)(reinterpret_cast<void*>(sys),reinterpret_cast<void*>(p.play.address),args);
  const auto published=local_read<TargetStringValue>(slot);
  if(args[8]>1||std::memcmp(args,&a,8)||std::memcmp(&published,&owned_array,sizeof(published))){frame.unknown=true;p.error=uncertain;return;}
  if(args[8]){terminal=3;p.state=3;return;}
  const auto current=helper.object_field(b,sys,"CurrentInWorldDialogueWidget");
  uint64_t widget_field=0;
  if(!current||!e33_mesh::named(b,local_read<uint64_t>(current+16),"WBP_DialogNotifBox_C","/Game/UI/Widgets/HUD_Exploration/WBP_DialogNotifBox")||
     !picto_field(b,current,"InWorldDialogue","ObjectProperty",848,8,&widget_field)||local_read<uint64_t>(current+848)!=a){frame.unknown=true;p.error=uncertain;return;}
  widget=call_capture(b,current);TargetStrongReferenceOps hold{b,widget};
  if(pool.acquire(hold,s,current,widget_token)!=StrongLeaseResult::Ok||!stabilize_retained_identity(hold,widget)){frame.unknown=true;p.error=uncertain;return;}
  bool playing=false;if(!query_playing(b,p.query.address,helper,playing)||!playing){frame.unknown=true;p.error=uncertain;return;}
  seen_playing=true;p.state=1;
 }
};
}
