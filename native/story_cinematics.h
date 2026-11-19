#pragma once
#include "story_cinematic_routes_packet.h"
namespace e33_story_cinematics {
struct Dispatcher{
 uint64_t base=0,session=0,owner=0;CallIdentity ids[count]{},menu[2]{},menu_direction{},menu_arrows[2]{},pending_world{};uint64_t leases[count]{};
 uint32_t route_count=0,keys[64][4]{},nkeys=0,selected=0,choices=0,target=0,routed=0,vanilla=0;unsigned hooks=0,routes=0;DWORD thread=0;bool unknown=false,pending_custom=false;
 inline static Dispatcher*live=nullptr;
 bool active()const{return owner||hooks||routes;}
 void poll(){if(!owner||unknown||!pending_custom||!pending_world.address)return;e33_dialogue_text::Dispatcher helper;const auto pc=zone_ref(base,ids[1].address,"PlayerController"),world=helper.world(base,pc);if(world&&exact_name(base,world+24,"Level_MainMenu")){pending_custom=false;pending_world={};}}
 bool protects(uint64_t token)const{if(!active())return false;for(auto v:leases)if(v==token)return true;return false;}
 bool bound(uint64_t world){
  for(unsigned i=0;i<nkeys;++i){e33_story_action::Dispatcher check;check.base=base;check.gi=ids[0];std::memcpy(check.guid,keys[i],16);if(check.bound())return true;}
  if(!pending_custom)return false;
  // The explicit custom-story Apply authorizes only its first world visit.
  // Subsequent maps/reloads require the exact persisted allow-listed GUID.
  auto now=call_capture(base,world);if(!now.address||exact_name(base,world+24,"Level_MainMenu"))return false;
  if(!pending_world.address)pending_world=now;
  if(pending_world.index!=now.index||pending_world.address!=now.address||
     (pending_world.serial>0&&pending_world.serial!=now.serial))return false;
  if(!pending_world.serial)pending_world=now;return true;
 }
 e33_blueprint_transform::Decision begin(uint64_t fn,void*object,void*frame){
  if(!owner||unknown||thread!=GetCurrentThreadId())return {};
  const auto actor=reinterpret_cast<uint64_t>(object),f=reinterpret_cast<uint64_t>(frame);
  if(!f||local_read<uint64_t>(f+0x10)!=fn||local_read<uint64_t>(f+0x18)!=actor)return {};
  if(fn==ids[4].address){
   if(choices&&actor){
    if(call_identity(base,menu_arrows[0])==actor)selected=(selected+choices-1)%choices;
    else if(call_identity(base,menu[0])==actor||call_identity(base,menu_arrows[1])==actor)selected=(selected+1)%choices;
   }
   return {};
  }
  if(fn==ids[5].address){if(call_identity(base,menu[1])==actor&&choices){pending_custom=selected==target;pending_world={};}return {};}
  if(fn!=ids[2].address||!picto_class(base,actor,"BP_CinematicSystem_C","/Game/Gameplay/CinematicSystem/BP_CinematicSystem"))return {};
  e33_dialogue_text::Dispatcher helper;const auto controller=local_read<uint64_t>(actor+32),world=helper.world(base,controller);
  if(!world||zone_ref(base,world,"OwningGameInstance")!=ids[0].address||
     zone_ref(base,ids[1].address,"PlayerController")!=controller||zone_ref(base,controller,"Player")!=ids[1].address||
     helper.world(base,actor)!=world||!bound(world)){++vanilla;return {};}
  const auto locals=local_read<uint64_t>(f+0x28);if(!locals)return {};
  const auto path=local_read<uint64_t>(locals+8);const uint8_t empty[16]{};
  if(std::memcmp(reinterpret_cast<void*>(locals+24),empty,16))return {};
  for(unsigned i=6;i<6+2*route_count;i+=2){
   if(!call_identity(base,ids[i])||!call_identity(base,ids[i+1])){unknown=true;return {};}
   const auto package=local_read<uint64_t>(ids[i].address+32);
   if(path!=local_read<uint64_t>(package+24)||local_read<uint64_t>(locals+16)!=local_read<uint64_t>(ids[i].address+24))continue;
   // Rewrite this call's soft reference only. No cooked asset, save or
   // inventory property is changed, and the empty subpath owns no allocation.
   uint64_t zero=0;std::memcpy(reinterpret_cast<void*>(locals),&zero,8);
   const auto target_package=local_read<uint64_t>(ids[i+1].address+32);
   std::memcpy(reinterpret_cast<void*>(locals+8),reinterpret_cast<void*>(target_package+24),8);
   std::memcpy(reinterpret_cast<void*>(locals+16),reinterpret_cast<void*>(ids[i+1].address+24),8);
   ++routed;break;
  }
  return {};
 }
 static e33_blueprint_transform::Decision pre(void*ctx,uint64_t fn,void*object,void*frame){auto*self=static_cast<Dispatcher*>(ctx);__try{return self->begin(fn,object,frame);}__except(EXCEPTION_EXECUTE_HANDLER){self->unknown=true;return {};}}
 static void post(void*,uint64_t){}
 static void on_direction(void* ctx,void* object,unsigned direction){
  auto& self=*static_cast<Dispatcher*>(ctx);
  if(!self.owner||self.unknown||self.thread!=GetCurrentThreadId()||direction>1||!self.choices||
     call_identity(self.base,self.menu_direction)!=reinterpret_cast<uint64_t>(object))return;
  self.selected=(self.selected+(direction==0?self.choices-1:1))%self.choices;
 }
 static void __fastcall wrapper(void*object,void*frame,void*result){auto*self=live;if(!self)return;const auto fn=local_read<uint64_t>(reinterpret_cast<uint64_t>(frame)+0x10);pre(self,fn,object,frame);reinterpret_cast<e33_trace::Entry>(self->base+0x13937a0)(object,frame,result);}
 bool close(){if(unknown)return false;const unsigned inputs[]={2};while(hooks){auto fn=ids[inputs[hooks-1]].address;if(InterlockedCompareExchangePointer(reinterpret_cast<void*volatile*>(fn+0xd8),reinterpret_cast<void*>(base+0x13937a0),reinterpret_cast<void*>(wrapper))!=reinterpret_cast<void*>(wrapper)){unknown=true;return false;}--hooks;}e33_blueprint_transform::detach(this);while(routes){if(!BlueprintDirectTrace::release_narrative(ids[inputs[routes-1]].address))return false;--routes;}e33_cinematic_choice::owner=nullptr;e33_cinematic_choice::observe=nullptr;e33_cinematic_choice::direction=nullptr;owner=0;live=nullptr;return true;}
 template<class Pool>void run(uint64_t b,uint64_t s,Pool&pool,Packet&p){
  if(!valid_bounds(p)){p.error=rejected;return;}
  if(p.mode){if(owner!=p.owner||session!=s||route_count!=p.route_count||std::memcmp(ids,p.ids,sizeof(ids))||std::memcmp(leases,p.leases,sizeof(leases))){p.error=rejected;return;}
   if(p.mode==4){if(!close()){p.error=uncertain;return;}}
   else if(p.mode==2){nkeys=p.nkeys;std::memcpy(keys,p.keys,sizeof(keys));pending_custom=false;pending_world={};}
   else if(p.mode==3){if(!p.choices||p.choices>32||p.selected>=p.choices||p.target>=p.choices||!call_identity(b,p.menu[0])||!call_identity(b,p.menu[1])||
       (p.menu_direction.address&&(!call_identity(b,p.menu_direction)||!picto_class(b,p.menu_direction.address,"WBP_SliderSelector_C","/Game/UI/Widgets/InGame_Menu/Settings/Selectors/WBP_SliderSelector")))){p.error=rejected;return;}
    CallIdentity arrows[2]{};
    if(p.menu_direction.address){
     const char* names[]={"WBP_ArrowButton_Downgrade","WBP_ArrowButton_Upgrade"};
     for(unsigned i=0;i<2;++i){
      auto& identity=arrows[i];
      identity=call_capture(b,zone_ref(b,p.menu_direction.address,names[i]));
      if(identity.serial<=0||!call_identity(b,identity)||
         !picto_class(b,identity.address,"WBP_ArrowButton_C","/Game/UI/Widgets/InGame_Menu/Stats_Panel/WBP_ArrowButton")){
       p.error=rejected;return;
      }
     }
    }
    std::memcpy(menu,p.menu,sizeof(menu));menu_direction=p.menu_direction;
    std::memcpy(menu_arrows,arrows,sizeof(arrows));
    selected=p.selected;choices=p.choices;target=p.target;}
   p.routed=routed;p.vanilla=vanilla;p.state=p.mode+1;return;
  }
  if(active()||unknown){p.error=rejected;return;}
  for(unsigned i=0;i<active_count(p);++i)if(!call_identity(b,p.ids[i])||p.ids[i].serial<=0||!p.leases[i]||!pool.owns_object(s,p.leases[i],p.ids[i].address)){p.error=rejected;return;}
  if(!picto_class(b,p.ids[0].address,"BP_jRPG_GI_Custom_C","/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_GI_Custom")||
     !e33_mesh::named(b,local_read<uint64_t>(p.ids[1].address+16),"LocalPlayer","/Script/Engine")||
     !exact_name(b,p.ids[2].address+24,"TriggerCinematic")||local_read<uint32_t>(p.ids[2].address+0xb0)!=201326592U||local_read<uint16_t>(p.ids[2].address+0xb6)!=344||
     !picto_struct_field(b,p.ids[2].address,"TriggerCinematicVariableStruct","StructProperty",0,336)||
     !picto_struct_field(b,p.ids[3].address,"Cinematic_LevelSequence_SequenceToPlay_135_4B36836C484EA1CF937A97AA20D5947A","SoftObjectProperty",0,40)||
     !exact_name(b,p.ids[4].address+24,"HandleButtonClicked")||!exact_name(b,p.ids[5].address+24,"OnStartGameSettingsApplied")){p.error=rejected;return;}
  for(unsigned i=6;i<active_count(p);++i)if(!picto_class(b,p.ids[i].address,"LevelSequence","/Script/LevelSequence")){p.error=rejected;return;}
  base=b;session=s;route_count=p.route_count;thread=GetCurrentThreadId();owner=p.owner;pending_custom=false;pending_world={};std::memcpy(ids,p.ids,sizeof(ids));std::memcpy(leases,p.leases,sizeof(leases));nkeys=p.nkeys;std::memcpy(keys,p.keys,sizeof(keys));live=this;
  const unsigned inputs[]={2};for(auto input:inputs){if(local_read<uint64_t>(ids[input].address+0xd8)!=base+0x13937a0||!BlueprintDirectTrace::retain_narrative(base,ids[input].address)||!e33_blueprint_transform::attach(this,ids[input].address,pre,post)){p.error=uncertain;unknown=true;return;}++routes;if(InterlockedCompareExchangePointer(reinterpret_cast<void*volatile*>(ids[input].address+0xd8),reinterpret_cast<void*>(wrapper),reinterpret_cast<void*>(base+0x13937a0))!=reinterpret_cast<void*>(base+0x13937a0)){p.error=uncertain;unknown=true;return;}++hooks;}
  e33_cinematic_choice::owner=this;e33_cinematic_choice::observe=[](void*ctx,void*object,void*frame){auto*self=static_cast<Dispatcher*>(ctx);if(!frame)return;const auto fn=local_read<uint64_t>(reinterpret_cast<uint64_t>(frame)+0x10);if(fn==self->ids[4].address||fn==self->ids[5].address)pre(self,fn,object,frame);};p.state=1;
  e33_cinematic_choice::direction=on_direction;
 }
};
}
