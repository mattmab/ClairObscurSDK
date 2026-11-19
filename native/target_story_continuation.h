#pragma once
#include "story_continuation_packet.h"
#include "target_story_rich_rewrite.h"
namespace e33_story_continuation {
struct Dispatcher {
 uint64_t base=0,session=0,owner=0,function_lease=0,gi_lease=0,source_lease=0,sequence=0;
 CallIdentity function{},gi{},source{},system{},dialogue{},world{};uint32_t guid[4]{};int choice=-1;
 DWORD thread=0;bool pending=false,routing=false,unknown=false,ending=false;uint8_t end_args[16]{};
 void*lease_pool=nullptr;uint64_t system_token=0,dialogue_token=0;
 bool(*acquire_object)(void*,uint64_t,uint64_t,CallIdentity&,uint64_t&)=nullptr;
 bool(*release_object)(void*,uint64_t,uint64_t,CallIdentity,uint64_t)=nullptr;
 bool active()const{return owner||routing||pending;}
 bool protects(uint64_t token)const{return active()&&(token==function_lease||token==gi_lease||token==source_lease||token==system_token||token==dialogue_token);}
 bool bound()const{
  e33_story_action::Dispatcher proof;proof.base=base;proof.gi=gi;std::memcpy(proof.guid,guid,16);return proof.bound();
 }
 uint64_t named_int(uint64_t object,const char*name)const{
  for(auto cls=local_read<uint64_t>(object+16),n=uint64_t(0);cls&&n++<32;cls=local_read<uint64_t>(cls+0x40))
   for(auto field=local_read<uint64_t>(cls+0x50),i=uint64_t(0);field&&i++<2048;field=local_read<uint64_t>(field+24))
    if(exact_name(base,field+32,name)&&exact_name(base,local_read<uint64_t>(field+8),"IntProperty")&&local_read<uint64_t>(field+16)==(cls|1)&&
       local_read<int32_t>(field+0x30)==1&&local_read<int32_t>(field+0x34)==4){const auto offset=local_read<int32_t>(field+0x44);return offset>=40&&offset<65536?object+uint32_t(offset):0;}
  return 0;
 }
 e33_blueprint_transform::Decision begin(uint64_t f,void*object,void*frame){
  if(unknown||thread!=GetCurrentThreadId()||f!=function.address||!call_identity(base,function)||!bound())return {};
  const auto sys=reinterpret_cast<uint64_t>(object),stack=reinterpret_cast<uint64_t>(frame);
  if(!call_capture(base,sys).address||!picto_class(base,sys,"BP_DialogueSystemComponent_C","/Game/Gameplay/DialogueSystem/BP_DialogueSystemComponent")||!stack||
     local_read<uint64_t>(stack+0x10)!=f||local_read<uint64_t>(stack+0x90)||local_read<uint64_t>(stack+0x18)!=sys||
     local_read<uint64_t>(stack+0x20)!=local_read<uint64_t>(f+0x60))return {};
  const auto locals=local_read<uint64_t>(stack+0x28),d=locals?local_read<uint64_t>(locals):0;
  if(!call_capture(base,d).address||!call_identity(base,source)||local_read<uint64_t>(d+16)!=source.address)return {};
  e33_dialogue_text::Dispatcher helper;
  const auto controller=local_read<uint64_t>(sys+32),player=helper.object_field(base,controller,"Player"),w=helper.world(base,controller),last=named_int(sys,"LastChoice");
  if(!player||!e33_mesh::named(base,local_read<uint64_t>(player+16),"LocalPlayer","/Script/Engine")||
     helper.object_field(base,player,"PlayerController")!=controller||helper.object_field(base,sys,"ActiveDialogue")!=d||
     !w||helper.world(base,d)!=w||zone_ref(base,w,"OwningGameInstance")!=gi.address||!last)return {};
  const auto selected=local_read<int32_t>(last);if(selected!=0&&selected!=1)return {};
  if(pending){
   if(system.address!=sys||dialogue.address!=d){unknown=true;return {};}
   return {0,true};
  }
  system=call_capture(base,sys);dialogue=call_capture(base,d);world=call_capture(base,w);choice=selected;
  unknown=true;
  if(!acquire_object||!acquire_object(lease_pool,base,session,system,system_token)||!acquire_object(lease_pool,base,session,dialogue,dialogue_token))return {};
  unknown=false;++sequence;pending=true;
  ending=false;std::memset(end_args,0,sizeof(end_args));std::memcpy(end_args,reinterpret_cast<void*>(locals),10);
  // Deliberately defer the final native End only for this admitted original
  // flower. Its native choice, flower grant and quest updates already ran.
  return {0,true};
 }
 static e33_blueprint_transform::Decision pre(void*context,uint64_t f,void*object,void*frame){
  __try{return static_cast<Dispatcher*>(context)->begin(f,object,frame);}
  __except(EXCEPTION_EXECUTE_HANDLER){static_cast<Dispatcher*>(context)->unknown=true;return {};}
 }
 static void post(void*,uint64_t){}
 bool release_pending(){
  if(!release_object)return false;
  if(dialogue_token){if(!release_object(lease_pool,base,session,dialogue,dialogue_token))return false;dialogue_token=0;}
  if(system_token){if(!release_object(lease_pool,base,session,system,system_token))return false;system_token=0;}
  pending=false;ending=false;system={};dialogue={};world={};choice=-1;return true;
 }
 bool close(){
  if(unknown||pending)return false;
  if(routing){if(!e33_blueprint_transform::detach(this)||!BlueprintDirectTrace::release_narrative(function.address))return false;routing=false;}
  owner=0;return true;
 }
 bool admits(uint64_t b,uint64_t s,const CallIdentity&sys,const CallIdentity&d)const{
  return b==base&&s==session&&pending&&!ending&&!unknown&&bound()&&
   e33_retired_world::same(sys,system)&&e33_retired_world::same(d,dialogue)&&call_identity(b,source)&&call_identity(b,d)&&local_read<uint64_t>(d.address+16)==source.address;
 }
 template<class Pool>void run(uint64_t b,uint64_t s,Pool&pool,Packet&p){
  if(!valid(p)||unknown){p.error=unknown?uncertain:rejected;return;}
  if(p.mode){
   if(owner!=p.owner||session!=s||std::memcmp(&gi,&p.gi,16)||std::memcmp(&function,&p.function,16)||std::memcmp(&source,&p.source,16)||std::memcmp(guid,p.guid,16)||p.sequence>sequence){p.error=rejected;return;}
   if(p.mode==2||p.mode==4){
    // One-shot continuation of the copied original End arguments. Never
    // synthesize quest effects, a choice, or a successful reward here.
    e33_dialogue_text::Dispatcher helper;e33_retired_world::TargetOps proof{b};
    const bool retired=e33_retired_world::double_observe(proof,world)==e33_retired_world::Result::Retired;
    if(!pending||ending||p.sequence!=sequence){p.error=rejected;return;}
    if(!retired){
     uint64_t descriptor=0;const auto complete=call_identity(b,dialogue)?picto_field(b,dialogue.address,"IsComplete","BoolProperty",680,1,&descriptor):0;
     if(!bound()||!call_identity(b,system)||helper.object_field(b,system.address,"ActiveDialogue")!=dialogue.address||!complete||local_read<uint32_t>(descriptor+0x70)!=0xff010001U||
        (p.mode==2&&local_read<uint8_t>(complete)!=1)){p.error=rejected;return;}
     const auto dispatch=local_read<uint64_t>(local_read<uint64_t>(system.address)+0x268);
     if(dispatch!=b+0x1393330&&dispatch!=b+0x332bb90){p.error=rejected;return;}
     ending=true;unknown=true;
     reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(dispatch)(reinterpret_cast<void*>(system.address),reinterpret_cast<void*>(function.address),end_args);
     unknown=false;
    }else ending=true;
    p.state=p.mode+1;return;
   }
   if(p.mode==3){p.state=close()?4U:0U;if(!p.state)p.error=rejected;return;}
   if(pending&&ending){e33_dialogue_text::Dispatcher helper;e33_retired_world::TargetOps proof{b};
    const auto retired=e33_retired_world::double_observe(proof,world);
    if(retired==e33_retired_world::Result::Retired||(call_identity(b,system)&&helper.object_field(b,system.address,"ActiveDialogue")!=dialogue.address)){
     if(!release_pending()){unknown=true;p.error=uncertain;return;}
    }
   }
   p.sequence=sequence;p.pending=pending?(ending?2U:1U):0U;
   if(pending){p.system=system;p.dialogue=dialogue;p.world=world;p.choice=choice;}
   p.state=2;return;
  }
  e33_dialogue_text::Dispatcher helper;
  if(active()||!pool.owns_object(s,p.function_lease,p.function.address)||!pool.owns_object(s,p.gi_lease,p.gi.address)||!pool.owns_object(s,p.source_lease,p.source.address)||
     !call_identity(b,p.function)||!call_identity(b,p.gi)||!call_identity(b,p.source)||!call_is_class(b,p.source.address)||!helper.schema(b,p.function.address,2)||
     !e33_mesh::named(b,p.source.address,"BP_Dialogue_Gardens_GustaveFlower_C","/Game/Narrative/Dialogs/LevelsDialogs/Lumiere/WalkAct1/BP_Dialogue_Gardens_GustaveFlower")){
   p.error=rejected;return;}
  base=b;session=s;owner=p.owner;function=p.function;gi=p.gi;source=p.source;function_lease=p.function_lease;gi_lease=p.gi_lease;source_lease=p.source_lease;std::memcpy(guid,p.guid,16);thread=GetCurrentThreadId();
  lease_pool=&pool;
  acquire_object=[](void*storage,uint64_t module,uint64_t id,CallIdentity&object,uint64_t&token)->bool{
   auto&references=*static_cast<Pool*>(storage);TargetStrongReferenceOps ops{module,object};
   return references.acquire(ops,id,object.address,token)==StrongLeaseResult::Ok&&stabilize_retained_identity(ops,object);
  };
  release_object=[](void*storage,uint64_t module,uint64_t id,CallIdentity object,uint64_t token)->bool{
   auto&references=*static_cast<Pool*>(storage);TargetStrongReferenceOps ops{module,object};
   return references.release(ops,id,token)==StrongLeaseResult::Ok;
  };
  if(!bound()||!e33_blueprint_transform::attach(this,function.address,pre,post)){owner=0;p.error=rejected;return;}
  if(!BlueprintDirectTrace::retain_narrative(b,function.address)){e33_blueprint_transform::detach(this);owner=0;p.error=rejected;return;}
  routing=true;p.state=1;
 }
};
}
