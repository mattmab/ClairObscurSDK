#pragma once
#include "story_dialogue_camera.h"
#include "component_transform_profiles.h"
#include <cmath>
namespace e33_story_camera {
struct Dispatcher {
 bool unknown=false;uint64_t last_nonce=0;
#if E33_RUNTIME_CINEMATIC_VERSION>=278
 CallIdentity saved_system{},saved_dialogue{},saved_controller{},saved_world{},saved_target{},saved_getter{},saved_setter{},last_camera_owner{};
 uint64_t saved_token=0,saved_session=0,saved_owner=0,saved_dialogue_lease=0;
 template<class Pool> bool release_view(uint64_t b,uint64_t session,Pool& leases){
  if(saved_token){TargetStrongReferenceOps ops{b,saved_target};
   if(leases.release(ops,session,saved_token)!=StrongLeaseResult::Ok)return false;}
  saved_token=0;saved_session=0;saved_owner=0;saved_dialogue_lease=0;saved_system={};saved_dialogue={};saved_controller={};saved_world={};saved_target={};
  saved_getter={};saved_setter={};last_camera_owner={};return true;
 }
 template<class Pool,class Dialogues> bool restore_view(uint64_t b,uint64_t session,Pool& leases,
     const CallIdentity& system,const CallIdentity& dialogue,Dialogues& helpers){
  if(!saved_token)return true;
  if(saved_session!=session){saved_token=0;saved_session=0;return true;}
  if(unknown||std::memcmp(&system,&saved_system,sizeof(system))||std::memcmp(&dialogue,&saved_dialogue,sizeof(dialogue)))return false;
  const auto controller=call_identity(b,saved_controller),original_target=call_identity(b,saved_target);
  if(!controller||!original_target||!call_identity(b,saved_world)||helpers.world(b,controller)!=saved_world.address)return false;
  uint64_t current=0;
  if(!e33_engine_profile_call::invoke(b,saved_getter,saved_controller,e33_engine_profiles::profiles[7],&current))return false;
  // Never take the camera back from another service that acquired it meanwhile.
  if(current==last_camera_owner.address&&call_identity(b,last_camera_owner)==current){
   alignas(8) uint8_t args[24]{};std::memcpy(args,&original_target,8);
   unknown=true;
   if(!e33_engine_profile_call::invoke(b,saved_setter,saved_controller,e33_engine_profiles::profiles[6],args))return false;
   current=0;
   if(!e33_engine_profile_call::invoke(b,saved_getter,saved_controller,e33_engine_profiles::profiles[7],&current)||current!=original_target)return false;
   unknown=false;
  }
  return release_view(b,session,leases);
 }
#if E33_RUNTIME_CINEMATIC_VERSION>=279
 template<class Pool> void retire_view(uint64_t b,uint64_t session,Pool& leases,Packet& p){
  if(unknown){p.error=uncertain;return;}
  if(!valid(p)||p.retire!=1){p.error=rejected;return;}
  // Normal EndDialogue may already have released the journal. Retirement is
  // idempotent and never calls any method on an old-world object.
  if(!saved_token){p.state=1;return;}
  if(saved_session!=session||p.owner!=saved_owner||p.dialogue_lease!=saved_dialogue_lease||
     std::memcmp(&p.system,&saved_system,sizeof(p.system))||std::memcmp(&p.dialogue,&saved_dialogue,sizeof(p.dialogue))||
     !leases.owns_retirement_storage(session,p.dialogue_lease,p.dialogue.address)){
   p.error=rejected;return;
  }
  e33_retired_world::TargetOps ops{b};
  if(e33_retired_world::double_observe(ops,saved_world)!=e33_retired_world::Result::Retired){p.error=rejected;return;}
  if(!release_view(b,session,leases)){unknown=true;p.error=uncertain;return;}
  p.state=1;
 }
#endif
#endif
 bool function(uint64_t b,uint64_t fn,const char* owner,const char* path,const char* name,uint32_t flags,
               uint16_t size,const e33_dialogue_text::Parameter* expected,unsigned count)const{
  if(!e33_mesh::named(b,local_read<uint64_t>(fn+32),owner,path)||!exact_name(b,fn+24,name)||
     local_read<uint32_t>(fn+0xb0)!=flags||local_read<uint16_t>(fn+0xb6)!=size||
     local_read<uint16_t>(fn+0xb8)!=65535||local_read<uint64_t>(fn+0xd8)!=b+0x13937a0)return false;
  unsigned found=0,n=0;
  for(auto f=local_read<uint64_t>(fn+0x50);f&&n++<2048;f=local_read<uint64_t>(f+24)){
   if(!(local_read<uint64_t>(f+0x38)&128))continue;
   if(found>=count)return false;
   const auto& p=expected[found++];
   if(local_read<uint64_t>(f+16)!=(fn|1)||!exact_name(b,f+32,p.name)||!exact_name(b,local_read<uint64_t>(f+8),p.type)||
      local_read<int32_t>(f+0x30)!=1||local_read<int32_t>(f+0x34)!=p.width||local_read<int32_t>(f+0x44)!=p.offset||
      local_read<uint64_t>(f+0x38)!=p.flags)return false;
   const auto related=local_read<uint64_t>(f+0x70);
   if(!call_capture(b,related).address||!exact_name(b,related+24,p.related))return false;
   // UStruct PropertiesSize excludes final alignment padding. The dialogue
   // parameters contain seven bytes, while their reflected parameter slot is
   // eight bytes. Validate both independently rather than equating them.
   if(!std::strcmp(p.type,"StructProperty")&&local_read<int32_t>(related+0x58)!=
      (!std::strcmp(p.related,"S_DialogueParameters")?7:p.width))return false;
  }
  return found==count&&n<2048;
 }
 bool parameters(uint64_t b,uint64_t object,uint64_t& slot)const{
  uint64_t descriptor=0;
  slot=picto_field(b,object,"Dialogue Parameters","StructProperty",804,8,&descriptor);
  const auto type=slot?local_read<uint64_t>(descriptor+0x70):0;
  if(!type||!e33_mesh::named(b,type,"S_DialogueParameters","/Game/LevelTools/NPCs/S_DialogueParameters")||local_read<int32_t>(type+0x58)!=7)return false;
  const char* names[]={"ForcedDialogueStage_10_B89CD7564A8FB456779FB384B09D300D","ShouldTeleportCharacter_16_E223CDEA41F36AE8D9A83688653D4AAD",
   "UseDialogCameras_15_D88B2D884849450BB31F7583511E80B5","ForceCharacterWorld_19_44D0D9B0478E0DA302912AA3E4A325ED"};
  const char* types[]={"IntProperty","BoolProperty","BoolProperty","ByteProperty"};const int offsets[]={0,4,5,6},widths[]={4,1,1,1};
  unsigned found=0,n=0;
  for(auto f=local_read<uint64_t>(type+0x50);f&&n++<16;f=local_read<uint64_t>(f+24)){
   if(found>=4)return false;
   const unsigned i=found++;
   if(local_read<uint64_t>(f+16)!=(type|1)||!exact_name(b,f+32,names[i])||!exact_name(b,local_read<uint64_t>(f+8),types[i])||
      local_read<int32_t>(f+0x30)!=1||local_read<int32_t>(f+0x34)!=widths[i]||local_read<int32_t>(f+0x44)!=offsets[i])return false;
   if((i==1||i==2)&&local_read<uint32_t>(f+0x70)!=0xff010001U)return false;
  }
  return found==4&&n<16;
 }
 template<class Pool,class Dialogues> void run(uint64_t b,uint64_t session,Pool& leases,Packet& p,Dialogues& helpers){
  if(unknown){p.error=uncertain;return;}
  if(!valid(p)||p.retire||p.nonce==last_nonce||!TargetPodSchemaOps{b}.context()){p.state=101;p.error=rejected;return;}
  const auto sys=call_identity(b,p.system),dlg=call_identity(b,p.dialogue),npc=call_identity(b,p.npc),camera_npc=call_identity(b,p.camera_npc);
  const auto setter=call_identity(b,p.setter),handler=call_identity(b,p.handler);
  if(!sys||!dlg||!npc||!camera_npc||!setter||!handler||!leases.owns_object(session,p.dialogue_lease,dlg)||
     !e33_mesh::named(b,local_read<uint64_t>(sys+16),"BP_DialogueSystemComponent_C","/Game/Gameplay/DialogueSystem/BP_DialogueSystemComponent")||
     !e33_mesh::named(b,local_read<uint64_t>(dlg+16),"BP_Dialogue_C","/Game/Gameplay/DialogueSystem/BP_Dialogue")||
     helpers.object_field(b,sys,"ActiveDialogue")!=dlg||helpers.object_field(b,dlg,"NPC")!=npc){p.state=102;p.error=rejected;return;}
  const auto controller=local_read<uint64_t>(sys+32),local=helpers.object_field(b,controller,"Player"),world=helpers.world(b,controller);
  if(!local||!world||helpers.object_field(b,local,"PlayerController")!=controller||helpers.world(b,dlg)!=world||
     helpers.world(b,npc)!=world||helpers.world(b,camera_npc)!=world){p.state=103;p.error=rejected;return;}
  const auto camera=helpers.object_field(b,camera_npc,"Camera_Main_Dialogue");
  if(!camera||local_read<uint64_t>(camera+32)!=camera_npc||
     !e33_mesh::named(b,local_read<uint64_t>(camera+16),"CineCameraComponent","/Script/CinematicCamera")){p.state=104;p.error=rejected;return;}
  constexpr e33_dialogue_text::Parameter set_fields[]={{"DialogueParameters","StructProperty",0,8,2251869606903956ULL,"S_DialogueParameters"}};
  constexpr e33_dialogue_text::Parameter camera_fields[]={
   {"CameraType","ByteProperty",0,1,2251869606904468ULL,"EDialogueCameraType"},
#if E33_RUNTIME_CINEMATIC_VERSION>=278
   {"Parameters","StructProperty",8,56,2252349703717270ULL,"S_DialogueCameraParameters"}};
  const char* camera_function="ActivateCameraComponentByType";constexpr uint32_t camera_flags=214171648U;
#else
   {"Parameters","StructProperty",8,56,2252349703717268ULL,"S_DialogueCameraParameters"}};
  const char* camera_function="HandleCameraType";constexpr uint32_t camera_flags=205783040U;
#endif
  uint64_t slot=0;
  if(!parameters(b,dlg,slot)||!function(b,setter,"BP_Dialogue_C","/Game/Gameplay/DialogueSystem/BP_Dialogue","SetDialogueParameters",201457664U,8,set_fields,1)||
     !function(b,handler,"BP_DialogueSystemComponent_C","/Game/Gameplay/DialogueSystem/BP_DialogueSystemComponent",camera_function,camera_flags,64,camera_fields,2)){
   p.state=105;p.error=rejected;return;
  }
  Parameters before{},next{};std::memcpy(&before,reinterpret_cast<void*>(slot),8);CameraArguments arguments{};
  if(!enable_camera(before,next)||!camera_arguments(camera,arguments)){p.state=106;p.error=rejected;return;}
  const auto dispatch=local_read<uint64_t>(local_read<uint64_t>(sys)+0x268),dialog_dispatch=local_read<uint64_t>(local_read<uint64_t>(dlg)+0x268);
  if((dispatch!=b+0x1393330&&dispatch!=b+0x332bb90)||(dialog_dispatch!=b+0x1393330&&dialog_dispatch!=b+0x332bb90)){p.state=107;p.error=rejected;return;}
  const bool frame=p.pose_setter.address!=0;
  const auto camera_id=call_capture(b,camera);
  alignas(16) uint8_t pose_arguments[368]{};
  double requested[12]{};
  if(frame){
   const auto set=call_identity(b,p.pose_setter),get=call_identity(b,p.pose_getter);
   e33_engine_profile_call::TargetOps set_ops{b,set,camera,e33_component_transform::set_relative,nullptr};
   e33_engine_profile_call::TargetOps get_ops{b,get,camera,e33_component_transform::get_relative,nullptr};
   if(!set||!get||!set_ops.context()||!set_ops.identities()||!set_ops.exact_profile()||!set_ops.recipient_derives()||!set_ops.dispatch_entry()||
      !get_ops.context()||!get_ops.identities()||!get_ops.exact_profile()||!get_ops.recipient_derives()||!get_ops.dispatch_entry()){
    p.state=108;p.error=rejected;return;
   }
   speaker_pose(requested);
  }
#if E33_RUNTIME_CINEMATIC_VERSION>=278
  // The shared lease pool retires these references when its SDK session closes.
  // Never reuse that session's journal/token in a later session.
  if(saved_token&&saved_session!=session){saved_token=0;saved_session=0;}
  const auto get_view=call_identity(b,p.view_getter),set_view=call_identity(b,p.view_setter);
  e33_engine_profile_call::TargetOps get_ops{b,get_view,controller,e33_engine_profiles::profiles[7],nullptr};
  e33_engine_profile_call::TargetOps set_ops{b,set_view,controller,e33_engine_profiles::profiles[6],nullptr};
  if(!get_view||!set_view||!get_ops.context()||!get_ops.identities()||!get_ops.exact_profile()||!get_ops.recipient_derives()||!get_ops.dispatch_entry()||
     !set_ops.context()||!set_ops.identities()||!set_ops.exact_profile()||!set_ops.recipient_derives()||!set_ops.dispatch_entry()){
   p.state=109;p.error=rejected;return;
  }
  if(saved_token&&(!call_identity(b,saved_world)||saved_world.address!=world)){
   if(!release_view(b,session,leases)){unknown=true;p.error=uncertain;return;}
  }
  if(saved_token&&(std::memcmp(&saved_dialogue,&p.dialogue,sizeof(p.dialogue))||
     std::memcmp(&saved_system,&p.system,sizeof(p.system)))){p.state=110;p.error=rejected;return;}
  uint64_t current=0;
  if(!e33_engine_profile_call::invoke(b,p.view_getter,call_capture(b,controller),e33_engine_profiles::profiles[7],&current)){
   p.state=111;p.error=rejected;return;
  }
  if(saved_token&&!observed_view_allowed(current,last_camera_owner.address,saved_target.address,npc,camera_npc)){
   // Player-speaker lines in the original Blueprint can restore the current
   // possessed pawn before our authored speaker framing runs. All active
   // dialogue ownership, local controller and world proofs above still apply;
   // never admit an unrelated cinematic/service view target here.
   const auto pawn=helpers.object_field(b,controller,"Pawn");
   const auto pawn_id=call_capture(b,pawn);
   if(!dialogue_pawn_view_allowed(current,pawn,pawn?helpers.object_field(b,pawn,"Controller"):0,
        controller,pawn?helpers.world(b,pawn):0,world,pawn_id.address==pawn&&pawn!=0)){
    p.state=112;p.error=rejected;return;
   }
  }
  if(!saved_token){
   auto captured_target=call_capture(b,current);
   if(!captured_target.address||helpers.world(b,current)!=world){p.state=113;p.error=rejected;return;}
   TargetStrongReferenceOps ops{b,captured_target};uint64_t token=0;
   if(leases.acquire(ops,session,current,token)!=StrongLeaseResult::Ok){unknown=true;p.error=uncertain;return;}
   saved_token=token;saved_session=session;saved_owner=p.owner;saved_dialogue_lease=p.dialogue_lease;
   saved_target=captured_target;saved_world=call_capture(b,world);saved_controller=call_capture(b,controller);
   saved_system=p.system;saved_dialogue=p.dialogue;saved_getter=p.view_getter;saved_setter=p.view_setter;
  }
#endif
  unknown=true;last_nonce=p.nonce;
  if(frame){
   std::memcpy(pose_arguments,requested,96);pose_arguments[352]=1;
   if(!e33_engine_profile_call::invoke(b,p.pose_setter,camera_id,e33_component_transform::set_relative,pose_arguments)){
    p.error=uncertain;return;
   }
   std::memset(pose_arguments,0,sizeof(pose_arguments));
   if(!e33_engine_profile_call::invoke(b,p.pose_getter,camera_id,e33_component_transform::get_relative,pose_arguments)){
    p.error=uncertain;return;
   }
   double actual[12]{};std::memcpy(actual,pose_arguments,96);
   for(unsigned i=0;i<12;++i){
    if(i==7||i==11)continue;
    if(!std::isfinite(actual[i])||std::fabs(actual[i]-requested[i])>0.0001){p.error=uncertain;return;}
   }
  }
#if E33_RUNTIME_CINEMATIC_VERSION<278 || E33_RUNTIME_CINEMATIC_VERSION>=283
  reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(dialog_dispatch)(reinterpret_cast<void*>(dlg),reinterpret_cast<void*>(setter),&next);
  if(std::memcmp(reinterpret_cast<void*>(slot),&next,8)){p.error=uncertain;return;}
#endif
  reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(dispatch)(reinterpret_cast<void*>(sys),reinterpret_cast<void*>(handler),&arguments);
  if(helpers.object_field(b,sys,"CurrentCameraComponent")!=camera){p.error=uncertain;return;}
#if E33_RUNTIME_CINEMATIC_VERSION>=278
#if E33_RUNTIME_CINEMATIC_VERSION>=282
  // Activating the component does not guarantee the controller left the
  // gameplay pawn (in particular after an original dialogue line refresh).
  // Only the reviewed owned carrier may become this conversation's view.
  alignas(8) uint8_t view_arguments[24]{};std::memcpy(view_arguments,&camera_npc,8);
  if(!e33_engine_profile_call::invoke(b,p.view_setter,call_capture(b,controller),e33_engine_profiles::profiles[6],view_arguments)){
   p.error=uncertain;return;
  }
  current=0;
  if(!e33_engine_profile_call::invoke(b,p.view_getter,call_capture(b,controller),e33_engine_profiles::profiles[7],&current)||current!=camera_npc){
   p.error=uncertain;return;
  }
#endif
#if E33_RUNTIME_CINEMATIC_VERSION>=283
  if(std::memcmp(reinterpret_cast<void*>(slot),&next,8)){p.error=uncertain;return;}
#else
  if(std::memcmp(reinterpret_cast<void*>(slot),&before,8)){p.error=uncertain;return;}
#endif
  last_camera_owner=p.camera_npc;
#endif
  unknown=false;p.state=1;
 }
};
}
