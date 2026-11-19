#pragma once
#include "story_dialogue_participants.h"
#include "owned_action_array_copy.h"
namespace e33_story_participants {
struct Dispatcher {
 bool registered=false,unknown=false;
 CallIdentity system{},dialogue{};uint64_t world=0,nonce=0,owner=0,player=0;
 uint32_t count=0;Participant participants[capacity]{};
 List installed_slots{},installed_actors{};
 bool read_list(uint64_t b,uint64_t slot,List& out)const{
  const auto data=local_read<uint64_t>(slot);const auto n=local_read<int32_t>(slot+8),cap=local_read<int32_t>(slot+12);
  if(n<0||n>int(capacity+2)||cap<n||cap>4096||(cap&&(!data||(data&7))))return false;
  out={};out.count=uint32_t(n);
  for(uint32_t i=0;i<out.count;++i){out.values[i]=local_read<uint64_t>(data+uint64_t(i)*8);if(!call_capture(b,out.values[i]).address)return false;}
  return true;
 }
 bool equal(const List&a,const List&b)const{return a.count==b.count&&!std::memcmp(a.values,b.values,a.count*8);}
 uint64_t array_field(uint64_t b,uint64_t object,const char* name,int offset,uint64_t& descriptor)const{
  auto slot=picto_field(b,object,name,"ArrayProperty",offset,16,&descriptor);
  if(!slot||local_read<uint64_t>(descriptor)!=b+0x6e0de80||local_read<uint64_t>(descriptor+0x38)!=67589ULL)return 0;
  const auto inner=local_read<uint64_t>(descriptor+0x78);
  if(!inner||local_read<uint64_t>(inner+16)!=descriptor||!exact_name(b,local_read<uint64_t>(inner+8),"ObjectProperty")||
     local_read<int32_t>(inner+0x30)!=1||local_read<int32_t>(inner+0x34)!=8||
     !e33_mesh::named(b,local_read<uint64_t>(inner+0x70),"Actor","/Script/Engine"))return 0;
  return slot;
 }
 bool copy_ready(uint64_t b)const{
  return local_read<uint64_t>(b+e33_action_clone::array_property_table+0xf0)==b+e33_action_clone::array_copy_entry&&
   !std::memcmp(reinterpret_cast<const void*>(b+e33_action_clone::array_copy_entry),e33_action_clone::array_copy_prefix,sizeof(e33_action_clone::array_copy_prefix));
 }
 void copy(uint64_t b,uint64_t descriptor,uint64_t slot,const List& values)const{
  struct Header {uint64_t data;int32_t count,capacity;};
  const Header source{reinterpret_cast<uint64_t>(values.values),int32_t(values.count),int32_t(values.count)};
  e33_action_clone::RootArrayCopy input{descriptor,reinterpret_cast<uint64_t>(&source),slot};
  e33_action_clone::dispatch_simon_array_copy(b,input);
 }
 template<class Pool,class Dialogues> void run(uint64_t b,uint64_t session,Pool& leases,Packet&p,Dialogues& helpers){
  if(unknown){p.error=uncertain;return;}
  if(!valid(p)||!TargetPodSchemaOps{b}.context()){p.error=rejected;return;}
  const auto sys=call_identity(b,p.system),dlg=call_identity(b,p.dialogue),fn=call_identity(b,p.update_actors);
  if(!sys||!dlg||!fn||!leases.owns_object(session,p.dialogue_lease,dlg)||
     !e33_mesh::named(b,local_read<uint64_t>(sys+16),"BP_DialogueSystemComponent_C","/Game/Gameplay/DialogueSystem/BP_DialogueSystemComponent")||
     !e33_mesh::named(b,local_read<uint64_t>(dlg+16),"BP_Dialogue_C","/Game/Gameplay/DialogueSystem/BP_Dialogue")){
   p.error=rejected;return;
  }
  const auto controller=local_read<uint64_t>(sys+32),local=helpers.object_field(b,controller,"Player"),current_world=helpers.world(b,controller);
  const auto active=helpers.object_field(b,sys,"ActiveDialogue"),npc=helpers.object_field(b,dlg,"NPC"),pawn=helpers.object_field(b,controller,"Pawn");
  if(!local||!current_world||!npc||!pawn||helpers.object_field(b,local,"PlayerController")!=controller||
     helpers.world(b,dlg)!=current_world||helpers.world(b,npc)!=current_world||(!p.mode&&active!=dlg)||(p.mode&&active)){
   p.error=rejected;return;
  }
  if(registered&&world!=current_world){registered=false;count=0;}
  if((!p.mode&&registered)||(p.mode&&(!registered||nonce!=p.nonce||!same(system,p.system)||!same(dialogue,p.dialogue)||
      count!=p.count||std::memcmp(participants,p.participants,count*sizeof(Participant))))){p.error=rejected;return;}
  List additions{};
  for(uint32_t i=0;i<p.count;++i){const auto actor=call_identity(b,p.participants[i].actor);
   if(!actor||!leases.owns_object(session,p.participants[i].lease,actor)||helpers.world(b,actor)!=current_world||!append(additions,actor)){
    p.error=rejected;return;
   }
  }
  if(!contains(additions,npc)){p.error=rejected;return;}
  uint64_t slots_descriptor=0,actors_descriptor=0;
  const auto slots=array_field(b,sys,"AvailableSpeakerSlots",344,slots_descriptor),actors=array_field(b,sys,"AllSpeakerActors",472,actors_descriptor);
  List old_slots{},old_actors{},next_slots{},next_actors{};
  if(!slots||!actors||!copy_ready(b)||!read_list(b,slots,old_slots)||!read_list(b,actors,old_actors)||
     !compose(old_slots,additions,npc,pawn,p.mode!=0,next_slots)||
     !compose(old_actors,additions,npc,pawn,true,next_actors)){
   p.error=rejected;return;
  }
  if(p.mode&&(!equal(old_slots,installed_slots)||!equal(old_actors,installed_actors))){p.error=rejected;return;}
  if(!p.mode){
   if(!e33_mesh::named(b,local_read<uint64_t>(fn+32),"BP_DialogueSystemComponent_C","/Game/Gameplay/DialogueSystem/BP_DialogueSystemComponent")||
      !exact_name(b,fn+24,"UpdateAllSpeakerActors")||local_read<uint32_t>(fn+0xb0)!=209977344U||
      local_read<uint16_t>(fn+0xb6)!=0||local_read<uint16_t>(fn+0xb8)!=65535||local_read<uint64_t>(fn+0xd8)!=b+0x13937a0){p.error=rejected;return;}
   unsigned n=0;for(auto field=local_read<uint64_t>(fn+0x50);field&&n++<2048;field=local_read<uint64_t>(field+24))
    if(local_read<uint64_t>(field+0x38)&128){p.error=rejected;return;}
   if(n>=2048){p.error=rejected;return;}
  }
  const auto dispatch=local_read<uint64_t>(local_read<uint64_t>(sys)+0x268);
  if(dispatch!=b+0x1393330&&dispatch!=b+0x332bb90){p.error=rejected;return;}
  // Durable uncertainty is published before engine allocation or dispatch.
  unknown=true;copy(b,slots_descriptor,slots,next_slots);
  if(!p.mode){
   reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(dispatch)(reinterpret_cast<void*>(sys),reinterpret_cast<void*>(fn),nullptr);
   if(!read_list(b,slots,installed_slots)||!equal(installed_slots,next_slots)||!read_list(b,actors,installed_actors)){p.error=uncertain;return;}
   for(uint32_t i=0;i<additions.count;++i)if(!contains(installed_actors,additions.values[i])){p.error=uncertain;return;}
   registered=true;system=p.system;dialogue=p.dialogue;world=current_world;nonce=p.nonce;owner=npc;player=pawn;count=p.count;
   std::memcpy(participants,p.participants,count*sizeof(Participant));
  }else{
   copy(b,actors_descriptor,actors,next_actors);List checked_slots{},checked_actors{};
   if(!read_list(b,slots,checked_slots)||!equal(checked_slots,next_slots)||!read_list(b,actors,checked_actors)||!equal(checked_actors,next_actors)){
    p.error=uncertain;return;
   }
   registered=false;count=0;
  }
  unknown=false;p.state=1;
 }
};
}
