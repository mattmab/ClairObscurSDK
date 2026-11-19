#pragma once
#include "story_action_packet.h"
#include "target_story_identity.h"
namespace e33_story_action {
struct Dispatcher {
 uint64_t base=0,session=0,owner=0,next=0,function_lease=0,gi_lease=0;CallIdentity function{},gi{};uint32_t guid[4]{};
 Source sources[8]{};uint32_t count=0,used=0;Receipt receipts[32]{};size_t hook=0;
 bool routing=false,lost=false;DWORD thread=0;
 bool active()const{return hook||routing;}
 bool protects(uint64_t token)const{
  if(!active())return false;
  if(token==function_lease||token==gi_lease)return true;
  for(unsigned i=0;i<count;++i)if(sources[i].lease==token)return true;
  return false;
 }
 // No allocations or engine calls in the trace callback. Validate the exact
 // save-carried marker with a bounded sparse-array scan before queuing a copy.
 bool bound()const{
  if(!call_identity(base,gi))return false;
  uint64_t descriptor=0;const auto map=picto_field(base,gi.address,"InteractedDialogues","MapProperty",3400,80,&descriptor);
  if(!map||!descriptor||local_read<uint8_t>(descriptor+0x98)&1||
     local_read<int32_t>(descriptor+0x80)!=16||local_read<int32_t>(descriptor+0x84)!=20||
     local_read<int32_t>(descriptor+0x88)!=24||local_read<int32_t>(descriptor+0x8c)!=28)return false;
  const auto n=local_read<int32_t>(map+8),cap=local_read<int32_t>(map+12),bits=local_read<int32_t>(map+40),
   bitcap=local_read<int32_t>(map+44),free=local_read<int32_t>(map+52);
  const auto data=local_read<uint64_t>(map),heap=local_read<uint64_t>(map+32),mask=heap?heap:map+16;
  if(n<0||n>cap||cap>8192||bits!=n||bitcap<bits||bitcap>16384||free<0||free>n||
     (!heap&&bitcap>128)||(n&&(!data||(data&3))))return false;
  int matches=0,live=0;
  for(int i=0;i<n;++i)if(local_read<uint32_t>(mask+uint64_t(i/32)*4)&(1U<<(i%32))){
   ++live;const auto at=data+uint64_t(i)*28;
   if(local_read<uint32_t>(at)!=e33_story_identity::prefix)continue;
   if(++matches>1||std::memcmp(reinterpret_cast<void*>(at),guid,16)||local_read<int32_t>(at+16)!=e33_story_identity::stage)return false;
  }return matches==1&&live==n-free;
 }
 void observe(void* object,void* frame){
  if(thread!=GetCurrentThreadId()||!bound()||!call_identity(base,function))return;
  const auto obj=reinterpret_cast<uint64_t>(object),f=reinterpret_cast<uint64_t>(frame);
  if(!obj||!f||!call_capture(base,obj).address||!picto_class(base,obj,"BP_GameActionExecutorComponent_C","/Game/Gameplay/GameActionsSystem/BP_GameActionExecutorComponent"))return;
  const auto script=local_read<uint64_t>(function.address+0x60);const auto size=local_read<int32_t>(function.address+0x68);
  const auto code=local_read<uint64_t>(f+0x20),locals=local_read<uint64_t>(f+0x28);
  if(local_read<uint64_t>(f+0x10)!=function.address||local_read<uint64_t>(f+0x90)!=(blueprint_direct_frame?0:function.address)||
     local_read<uint64_t>(f+0x18)!=obj||local_read<uint64_t>(f+0x80)||!locals||!script||size<1||size>1048576||code<script||code>script+uint64_t(size))return;
  const auto instance=local_read<uint64_t>(locals);
  if(!call_capture(base,instance).address||!picto_class(base,instance,"GameActionInstance","/Script/SandFall"))return;
  const auto action=picto_field(base,instance,"GameAction","ObjectProperty",40,8);
  if(!action)return;
  unsigned index=count;for(unsigned i=0;i<count;++i)if(call_identity(base,sources[i].object)&&local_read<uint64_t>(action)==sources[i].object.address){index=i;break;}
  if(index==count)return;
  e33_retired_world::Snapshot now{};e33_retired_world::TargetOps proof{base};
  if(!proof.observe(now)||zone_ref(base,now.world.address,"OwningGameInstance")!=gi.address)return;
  auto outer=obj;bool same_world=false;
  for(unsigned i=0;outer&&i<32;++i,outer=local_read<uint64_t>(outer+32))if(outer==now.world.address){same_world=true;break;}
  if(!same_world)return;
  if(used==32){lost=true;return;}
  receipts[used++]={++next,index,0,now.world};
 }
 static void callback(void*context,void*object,void*frame,void*){
  __try{static_cast<Dispatcher*>(context)->observe(object,frame);}__except(EXCEPTION_EXECUTE_HANDLER){static_cast<Dispatcher*>(context)->lost=true;}
 }
 bool close(){
  if(hook){if(!e33_trace::TraceSlots<>::remove(hook))return false;hook=0;}
  if(routing){if(!BlueprintDirectTrace::release_story_action())return false;routing=false;}
  owner=0;count=used=0;return true;
 }
 template<class Pool>void run(uint64_t b,uint64_t s,Pool&pool,Packet&p){
  if(!valid(p)){p.error=rejected;return;}
  if(p.mode){
   if(owner!=p.owner||session!=s||thread!=GetCurrentThreadId()||std::memcmp(&function,&p.function,16)||std::memcmp(&gi,&p.gi,16)||std::memcmp(guid,p.guid,16)||count!=p.count||std::memcmp(sources,p.sources,sizeof(sources))){p.error=rejected;return;}
   if(p.mode==2){p.state=close()?3U:0U;if(!p.state)p.error=rejected;return;}
   if(lost){p.error=overflow;return;}
   // These are immutable receipts captured while bound() proved the original
   // save. The exact owner/session/GUID/source journal above authorizes draining
   // them even after title or another save clears the live marker. The callback
   // still requires bound() before recording any new completion.
   // Acknowledgement removes only receipts the caller has already consumed.
   unsigned keep=0;for(unsigned i=0;i<used;++i)if(receipts[i].sequence>p.after)receipts[keep++]=receipts[i];used=keep;
   p.used=used;for(unsigned i=0;i<used;++i)p.receipts[i]=receipts[i];p.state=2;return;
  }
  if(active()||!pool.owns_object(s,p.function_lease,p.function.address)||!pool.owns_object(s,p.gi_lease,p.gi.address)){p.error=rejected;return;}
  for(unsigned i=0;i<p.count;++i)if(!pool.owns_object(s,p.sources[i].lease,p.sources[i].object.address)){p.error=rejected;return;}
  const auto f=call_identity(b,p.function);
  if(!f||!e33_mesh::named(b,local_read<uint64_t>(f+32),"BP_GameActionExecutorComponent_C","/Game/Gameplay/GameActionsSystem/BP_GameActionExecutorComponent")||
     !exact_name(b,f+24,"OnGameActionExecutionFinished")||local_read<uint32_t>(f+0xb0)!=0xc040000||local_read<uint16_t>(f+0xb6)!=8||local_read<uint64_t>(f+0xd8)!=b+0x13937a0){p.error=rejected;return;}
  const auto field=picto_struct_field(b,f,"GameActionInstance","ObjectProperty",0,8);
  if(!field||local_read<uint64_t>(field+0x38)!=0x8001000000294ULL||!e33_mesh::named(b,local_read<uint64_t>(field+0x70),"GameActionInstance","/Script/SandFall")){p.error=rejected;return;}
  base=b;session=s;owner=p.owner;function=p.function;gi=p.gi;function_lease=p.function_lease;gi_lease=p.gi_lease;std::memcpy(guid,p.guid,16);std::memcpy(sources,p.sources,sizeof(sources));count=p.count;thread=GetCurrentThreadId();used=0;next=0;lost=false;
  if(!bound()||!BlueprintDirectTrace::retain_story_action(b,f)){owner=0;p.error=rejected;return;}routing=true;
  hook=e33_trace::TraceSlots<>::install(reinterpret_cast<void*volatile*>(f+0xd8),reinterpret_cast<e33_trace::Entry>(b+0x13937a0),callback,this,false,true,true);
  if(!hook){close();p.error=rejected;return;}p.state=1;
 }
};
}
