#pragma once
#include "battle_completion_receipt.h"
#include "battle_completion_frame.h"
#include "battle_completion_schema.h"
#include "blueprint_direct_trace.h"
#include "retired_world_target.h"

// Internal native domain only: arm() requires an existing owned battle's proof
// callback. Never expose caller-selected FNames/source objects as proof. That
// owner must keep its private-name/source/arena registration alive until close.
// proof runs under TraceSlots lock: bounded reads only; never ProcessEvent,
// registration, retention, release, Python, or hook teardown.
class BattleCompletionOwner {
 uint64_t base_=0,session_=0;DWORD thread_=0;size_t hook_=0;bool routing_=false;
 CallIdentity ids_[5]{};uint64_t tokens_[5]{}; // world,controller,source,arena,function
 e33_battle_completion::Context context_{};
 e33_battle_completion::Journal journal_{};
 void* proof_context_=nullptr;
 bool (*proof_)(void*,const e33_battle_completion::Context&,bool)=nullptr;
 bool worldmap_=false;
 struct SchemaOps {
  uint64_t base;
  template<class T>T read(uint64_t a)const{return local_read<T>(a);}
  bool live(uint64_t a)const{return call_capture(base,a).address&&!(local_read<uint32_t>(a+8)&0x40018030U);}
  bool named(uint64_t a,const char* n)const{return exact_name(base,a,n);}
  bool is_class(uint64_t a)const{return call_is_class(base,a);}
  bool object_name(uint64_t a,const char* n,const char* package)const{
   return live(a)&&exact_name(base,a+24,n)&&live(local_read<uint64_t>(a+32))&&
    exact_name(base,local_read<uint64_t>(a+32)+24,package);
  }
 };
 static e33_battle_completion::Identity copy(const CallIdentity& i){return {i.index,i.serial,i.address};}
 bool current()const{
  if(thread_!=GetCurrentThreadId()||!TargetPodSchemaOps{base_}.context())return false;
  for(const auto& i:ids_)if(!call_identity(base_,i))return false;
  e33_retired_world::TargetOps ops{base_};e33_retired_world::Snapshot now{};
  return ops.observe(now)&&e33_retired_world::same(now.world,ids_[0])&&ops.controller_world(ids_[1],now.world);
 }
 bool schema()const{SchemaOps ops{base_};return e33_battle_completion::completion_schema(ops,ids_[4].address,ids_[1].address,worldmap_);}
 void post(void* object,void* frame){
  if(!hook_||journal_.state()!=e33_battle_completion::State::armed||
     reinterpret_cast<uint64_t>(object)!=ids_[1].address)return;
  if(!current()||!schema()||!proof_||!proof_(proof_context_,context_,true)){journal_.revoke();return;}
  const auto script=local_read<uint64_t>(ids_[4].address+0x60);
  const auto size=local_read<int32_t>(ids_[4].address+0x68);
  if(size<=0||size>1048576){journal_.uncertain();return;}
  e33_battle_completion::FrameInput input{};
  auto read=[](uint64_t a,void* out,unsigned n){return target_trace_read(a,out,n);};
  if(!e33_battle_completion::copy_post_frame(read,reinterpret_cast<uint64_t>(frame),ids_[4].address,
      ids_[1].address,script,static_cast<uint32_t>(size),blueprint_direct_frame,input)){journal_.uncertain();return;}
  if(!current()||!schema()||!proof_(proof_context_,context_,true)){journal_.revoke();return;}
  journal_.observe_post(context_,input.private_name,input.result,true,true);
 }
 static void callback(void* owner,void* object,void* frame,void*){
  __try{static_cast<BattleCompletionOwner*>(owner)->post(object,frame);}
  __except(EXCEPTION_EXECUTE_HANDLER){static_cast<BattleCompletionOwner*>(owner)->journal_.uncertain();}
 }
public:
 bool active()const{if(hook_||routing_)return true;for(auto t:tokens_)if(t)return true;return false;}
 bool protects(uint64_t token)const{for(auto t:tokens_)if(t&&t==token)return true;return false;}
 auto state()const{return journal_.state();}
 template<class Pool> uint32_t arm(uint64_t base,uint64_t session,Pool& pool,
     const CallIdentity (&ids)[5],uint64_t battle,uint64_t private_name,bool worldmap,
     void* proof_context,bool(*proof)(void*,const e33_battle_completion::Context&,bool)){
  if(active()||!session||!battle||!private_name||!proof||journal_.state()!=e33_battle_completion::State::fresh)return 3661;
  base_=base;session_=session;thread_=GetCurrentThreadId();worldmap_=worldmap;
  for(unsigned i=0;i<5;++i)ids_[i]=ids[i];
  context_={copy(ids_[0]),copy(ids_[1]),copy(ids_[2]),copy(ids_[3]),battle,private_name};
  proof_context_=proof_context;proof_=proof;
  if(ids_[0].serial<=0||!current()||!schema()||!proof_(proof_context_,context_,false))return 3661;
  // Never pin UWorld across combat/travel. Its copied positive serial is
  // revalidated through the current viewport at callback and consumption.
  for(unsigned i=1;i<5;++i){TargetStrongReferenceOps ops{base_,ids_[i]};
   if(pool.acquire(ops,session_,ids_[i].address,tokens_[i])!=StrongLeaseResult::Ok)return 3662;
  }
  if(!current()||!schema()||!proof_(proof_context_,context_,false)||!journal_.arm(context_,true))return 3661;
  if(!BlueprintDirectTrace::retain_completion(base_,ids_[4].address))return 3663;
  routing_=true;
  hook_=e33_trace::TraceSlots<>::install(reinterpret_cast<void* volatile*>(ids_[4].address+0xd8),
   reinterpret_cast<e33_trace::Entry>(base_+0x13937a0),callback,this,false,false);
  return hook_?0:3663;
 }
 bool take(uint64_t battle,e33_battle_completion::Receipt& receipt){
  receipt={};
  if(!current()||!schema()){journal_.revoke();return false;}
  // Existing owned-anchor proof deliberately requires battle quiescence. A
  // pending query during active combat must not revoke a valid registration.
  if(journal_.state()==e33_battle_completion::State::armed)return false;
  if(!proof_||!proof_(proof_context_,context_,true)){journal_.revoke();return false;}
  return journal_.take(battle,receipt);
 }
 template<class Pool>uint32_t close(uint64_t base,uint64_t session,Pool& pool){
  if(!active()){journal_.revoke();return 0;}
  if(base!=base_||session!=session_||thread_!=GetCurrentThreadId())return 3664;
  journal_.revoke();
  // Detach callback before releasing either routing or any retained storage.
  if(hook_){if(!e33_trace::TraceSlots<>::remove(hook_))return 3664;hook_=0;}
  if(routing_){if(!BlueprintDirectTrace::release_completion())return 3664;routing_=false;}
  for(auto& token:tokens_)if(token){TargetStrongReferenceOps ops{base_,{-1,0,0}};
   if(pool.release(ops,session_,token)!=StrongLeaseResult::Ok)return 407;token=0;}
  proof_=nullptr;proof_context_=nullptr;return 0;
 }
};
