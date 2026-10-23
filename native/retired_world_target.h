#pragma once
#include "retired_world_gate.h"
#include "retired_world_getter.h"
#include "console_construction.h"
#include "target_strong_reference.h"
#include "strong_lease_pool.h"
#include "stable_identity.h"
// Full production capability chain already declares zone_ref before this file.
namespace e33_retired_world {
struct TargetOps {
 uint64_t base;
 bool context()const{return TargetStrongReferenceOps{base,{}}.can_assign();}
 bool native_class(uint64_t cls,const char*name,const char*package)const{
  if(!call_capture(base,cls).address||!call_is_class(base,cls))return false;
  const auto outer=local_read<uint64_t>(cls+32);
  return exact_name(base,cls+24,name)&&call_capture(base,outer).address&&exact_name(base,outer+24,package)&&
   exact_name(base,local_read<uint64_t>(cls+16)+24,"Class");
 }
 bool live(uint64_t obj)const{return call_capture(base,obj).address&&!(local_read<uint32_t>(obj+8)&0x40018030U);}
 bool derives(uint64_t cls,const char*name,const char*package)const{
  for(unsigned n=0;cls&&n<64;++n,cls=local_read<uint64_t>(cls+0x40))
   if(native_class(cls,name,package))return true;
  return false;
 }
 uint64_t reference(uint64_t object,const char*owner,const char*name,const char*alternate=nullptr)const{
  if(!live(object))return 0;
  auto cls=local_read<uint64_t>(object+16);
  for(unsigned lineage=0;cls&&lineage<32;++lineage,cls=local_read<uint64_t>(cls+0x40)){
   unsigned walked=0;
   for(auto field=local_read<uint64_t>(cls+0x50);field&&++walked<512;field=local_read<uint64_t>(field+24)){
    if(!exact_name(base,field+32,name))continue;
    if(!native_class(cls,owner,"/Script/Engine")&&!(alternate&&native_class(cls,alternate,"/Script/Engine")))return 0;
    // Reuse the shipping reflected ObjectProperty guard, including owner,
    // descriptor vtable, dimension, width and bounded declaring-class extent.
    return zone_ref(base,object,name);
   }
  }return 0;
 }
 bool current_binding(CallIdentity engine,CallIdentity viewport,CallIdentity world)const{
  return context()&&call_identity(base,engine)&&call_identity(base,viewport)&&call_identity(base,world)&&
   reference(engine.address,"Engine","GameViewport")==viewport.address&&
   reference(viewport.address,"GameViewportClient","World")==world.address;
 }
 bool observe(Snapshot&out)const{
  out={};if(!context())return false;
  // Existing bounded singleton registry observation rejects duplicate engines.
  const auto engine=console_find(base,nullptr,"GameEngine");
  if(!live(engine)||!native_class(local_read<uint64_t>(engine+16),"GameEngine","/Script/Engine"))return false;
  const auto viewport=reference(engine,"Engine","GameViewport");
  if(!live(viewport)||!derives(local_read<uint64_t>(viewport+16),"GameViewportClient","/Script/Engine"))return false;
  const auto world=reference(viewport,"GameViewportClient","World");
  if(!live(world)||!native_class(local_read<uint64_t>(world+16),"World","/Script/Engine"))return false;
  out={call_capture(base,engine),call_capture(base,viewport),call_capture(base,world)};
  return out.engine.address&&out.viewport.address&&out.world.address&&context()&&
   reference(engine,"Engine","GameViewport")==viewport&&reference(viewport,"GameViewportClient","World")==world&&
   same(call_capture(base,engine),out.engine)&&same(call_capture(base,viewport),out.viewport)&&same(call_capture(base,world),out.world);
 }
 bool controller_world(CallIdentity controller,CallIdentity world)const{
  if(!call_identity(base,controller)||!call_identity(base,world)||!live(controller.address)||
     !derives(local_read<uint64_t>(controller.address+16),"PlayerController","/Script/Engine"))return false;
  auto outer=controller.address;
  for(unsigned n=0;outer&&n<32;++n,outer=local_read<uint64_t>(outer+32))if(outer==world.address){
   const auto player=reference(controller.address,"PlayerController","Player");
   return live(player)&&derives(local_read<uint64_t>(player+16),"LocalPlayer","/Script/Engine")&&
    reference(player,"Player","PlayerController","LocalPlayer")==controller.address;
  }return false;
 }
 bool owning_player(CallIdentity widget,CallIdentity&controller,uint32_t*diagnostic=nullptr)const{
  if(diagnostic)*diagnostic=20540;
  controller={};if(!context()||!call_identity(base,widget)||!live(widget.address))return false;
  const auto count=local_read<int32_t>(base+0x9361b84);const auto chunks=local_read<uint64_t>(base+0x9361b70);
  if(diagnostic)*diagnostic=20541;
  if(count<1||count>1000000||!chunks)return false;
  CallIdentity function{},constraint{};
  for(int32_t index=0;index<count;++index){
   const auto chunk=local_read<uint64_t>(chunks+uint64_t(index>>16)*8);if(!chunk)return false;
   const auto object=local_read<uint64_t>(chunk+uint64_t(index&65535)*24);
   if(!object||!exact_name(base,object+24,"GetOwningPlayer"))continue;
   if(!live(object)||!native_class(local_read<uint64_t>(object+16),"Function","/Script/CoreUObject")||
      !native_class(local_read<uint64_t>(object+32),"Widget","/Script/UMG"))continue;
   if(function.address){if(diagnostic)*diagnostic=20542;return false;}function=call_capture(base,object);
  }
  if(diagnostic)*diagnostic=20543;
  if(!function.address)return false;
  if(diagnostic)*diagnostic=20544;
  const auto fn=function.address,field=local_read<uint64_t>(fn+0x50);
  if(local_read<uint32_t>(fn+0xb0)!=1409418250U||local_read<uint16_t>(fn+0xb6)!=8||
     local_read<uint16_t>(fn+0xb8)!=0||local_read<int32_t>(fn+0x58)!=8||
     local_read<uint64_t>(fn+0xd8)!=base+0x30ff320||!field||local_read<uint64_t>(field+24)||
     local_read<uint64_t>(field)!=base+0x6e11d38||local_read<uint64_t>(field+16)!=(fn|1)||
     !exact_name(base,field+32,"ReturnValue")||local_read<uint32_t>(field+48)!=1||
     local_read<uint32_t>(field+52)!=8||local_read<uint32_t>(field+68)!=0||
     local_read<uint64_t>(field+56)!=6755468160534400ULL)return false;
  if(diagnostic)*diagnostic=20545;
  const auto cls=local_read<uint64_t>(field+0x70);
  if(!native_class(cls,"PlayerController","/Script/Engine"))return false;
  constraint=call_capture(base,cls);
  CallPacket packet{};packet.version=1;packet.parameter_size=packet.allocation_extent=8;
  packet.return_offset=0;packet.function_flags=1409418250U;packet.entry_rva=0x30ff320;
  packet.field_count=1;packet.target=widget;packet.function=function;
  auto&value=packet.fields[0];value.kind=CallObject;value.width=8;value.dimension=1;
  value.flags=6755468160534400ULL;value.constraint=constraint;
  std::memcpy(value.name,"ReturnValue",12);
  auto checked=packet;
  if(diagnostic)*diagnostic=20546;
  if(reflected_call(base,checked,nullptr,nullptr,nullptr,nullptr,true))return false;
  if(diagnostic)*diagnostic=20547;
  if(reflected_call(base,packet)||packet.outcome!=CallDispatchReturned)return false;
  const auto result=owning_player_output(packet,controller);
  if(diagnostic)*diagnostic=result==OwningPlayerResult::Null?20548:20549;
  if(result!=OwningPlayerResult::Valid)return false;
  if(!call_identity(base,controller)||!live(controller.address)||!context())return false;
  if(diagnostic)*diagnostic=0;return true;
 }
 template<class Pool>uint32_t acquire(Pool&pool,uint64_t session,CallIdentity id,uint64_t&token)const{
  auto preflight=pool.preflight(session,1);if(preflight!=StrongLeaseResult::Ok)return uint32_t(preflight);
  TargetStrongReferenceOps refs{base,id};return uint32_t(pool.acquire(refs,session,id.address,token));
 }
 bool stabilize(CallIdentity&id)const{TargetStrongReferenceOps refs{base,id};return stabilize_retained_identity(refs,id);}
 template<class Pool>uint32_t release(Pool&pool,uint64_t session,uint64_t token)const{
  TargetStrongReferenceOps refs{base,{}};auto result=pool.release(refs,session,token);
  return result==StrongLeaseResult::Ok?0:result==StrongLeaseResult::Deferred?407:2053;
 }
};
}
