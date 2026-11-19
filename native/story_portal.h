#pragma once
#include "zone_travel.h"
#include "story_portal_packet.h"
#include "target_native_dialogue.h"
#include "target_story_action.h"
namespace e33_story_portal {
struct Entry {
 Packet request{};uint32_t state=0,sequence=0,last_error=0,elapsed=0;ULONGLONG first_seen=0;
 bool active()const{return request.owner!=0;}
 bool bound(uint64_t base)const{e33_story_action::Dispatcher d;d.base=base;d.gi=request.zone.gi;std::memcpy(d.guid,request.guid,16);return d.bound();}
};
struct Dispatcher {
 Entry entries[8];bool unknown=false,running=false;
#if E33_RUNTIME_CINEMATIC_VERSION>=297
 uint64_t base=0;CallIdentity interaction{};bool routing=false;DWORD thread=0;
 bool(*carrier_proof)(uint64_t,const CallIdentity&)=nullptr;
 bool has_direct()const{for(const auto&e:entries)if(e.active()&&e.request.tail[1])return true;return false;}
 bool detach_direct(){
  if(routing){if(!e33_blueprint_transform::detach(this)||!BlueprintDirectTrace::release_narrative(interaction.address))return false;routing=false;}
  return true;
 }
 e33_blueprint_transform::Decision begin_direct(uint64_t f,void*object,void*frame){
  if(unknown||running||!routing||thread!=GetCurrentThreadId()||f!=interaction.address||!call_identity(base,interaction))return {};
  const auto npc=reinterpret_cast<uint64_t>(object),stack=reinterpret_cast<uint64_t>(frame);
  for(auto&e:entries){
   const auto&p=e.request;
   if(!e.active()||!p.tail[1]||npc!=p.npc.address||!call_identity(base,p.npc)||!e.bound(base)||!carrier_proof||!carrier_proof(p.carrier_owner,p.npc))continue;
   if(!stack||local_read<uint64_t>(stack+0x10)!=f||local_read<uint64_t>(stack+0x90)||
      local_read<uint64_t>(stack+0x18)!=npc||local_read<uint64_t>(stack+0x20)!=local_read<uint64_t>(f+0x60))return {0,true};
   const auto locals=local_read<uint64_t>(stack+0x28);
   e33_dialogue_text::Dispatcher helper;
   if(!locals||!call_identity(base,p.zone.controller)||!call_identity(base,p.world)||
      helper.object_field(base,p.zone.player.address,"PlayerController")!=p.zone.controller.address||
      helper.object_field(base,p.zone.controller.address,"Pawn")!=local_read<uint64_t>(locals)||
      helper.world(base,npc)!=p.world.address||helper.world(base,p.zone.controller.address)!=p.world.address||
      helper.object_field(base,p.system.address,"ActiveDialogue"))return {0,true};
   // Consume E before any NPC dialogue staging, camera move or input lock.
   // The prepared same-world landing is the only subsequent player move.
   if(latch(e.state,e.sequence)){e.first_seen=GetTickCount64();e.state=2;e.elapsed=0;e.last_error=0;}
   return {0,true};
  }
  return {};
 }
 static e33_blueprint_transform::Decision pre_direct(void*context,uint64_t f,void*object,void*frame){
  __try{return static_cast<Dispatcher*>(context)->begin_direct(f,object,frame);}
  __except(EXCEPTION_EXECUTE_HANDLER){static_cast<Dispatcher*>(context)->unknown=true;return {0,true};}
 }
 static void post_direct(void*,uint64_t){}
 bool attach_direct(uint64_t b,const CallIdentity&fn){
  if(routing)return interaction.index==fn.index&&interaction.serial==fn.serial&&interaction.address==fn.address;
  const auto f=call_identity(b,fn);
  if(!f||!e33_mesh::named(b,local_read<uint64_t>(f+32),"BP_jRPG_NPC_Dialog_C","/Game/LevelTools/NPCs/BP_jRPG_NPC_Dialog")||
     !exact_name(b,f+24,"OnInteractionRequested")||local_read<uint32_t>(f+0xb0)!=201457664U||
     local_read<uint16_t>(f+0xb6)!=9||local_read<uint16_t>(f+0xb8)!=65535||local_read<uint64_t>(f+0xd8)!=b+0x13937a0||
     !local_read<uint64_t>(f+0x60)||local_read<int32_t>(f+0x68)<1||local_read<int32_t>(f+0x68)>8192)return false;
  const auto actor=picto_struct_field(b,f,"InteractingWorldCharacter","ObjectProperty",0,8),instant=picto_struct_field(b,f,"Instant","BoolProperty",8,1);
  // This hook suppresses the exact owned carrier event; it never executes or
  // rewrites its bytecode. Validate its own ABI, not the unrelated inventory
  // AddItemToInventory bytecode profile (picto script index 8).
  if(!actor||!instant||local_read<uint32_t>(instant+0x70)!=0xff010001U||
     local_read<uint64_t>(actor+0x38)!=2251868533162644ULL||
     local_read<uint64_t>(instant+0x38)!=2251869606904468ULL)return false;
  base=b;interaction=fn;thread=GetCurrentThreadId();
  if(!e33_blueprint_transform::attach(this,f,pre_direct,post_direct))return false;
  if(!BlueprintDirectTrace::retain_narrative(b,f)){e33_blueprint_transform::detach(this);return false;}
  routing=true;return true;
 }
#endif
 bool active()const{for(const auto&e:entries)if(e.active()&&e.state==1)return true;return false;}
 bool protects(uint64_t token)const{for(const auto&e:entries)if(e.active()){
  for(auto held:e.request.leases)if(held==token)return true;
#if E33_RUNTIME_CINEMATIC_VERSION>=297
  uint64_t extra=0;std::memcpy(&extra,e.request.tail+48,8);if(extra&&extra==token)return true;
#endif
 }return false;}
 bool close(){if(running||unknown)return false;
#if E33_RUNTIME_CINEMATIC_VERSION>=297
  if(!detach_direct())return false;
#endif
  for(auto&e:entries)e.request.owner=0;return true;}
 uint64_t talking_slot(uint64_t b,uint64_t npc)const{
  auto cls=local_read<uint64_t>(npc+16);
  for(unsigned n=0;cls&&n<32;++n,cls=local_read<uint64_t>(cls+0x40)){
   auto f=local_read<uint64_t>(cls+0x50);
   for(unsigned i=0;f&&i<2048;++i,f=local_read<uint64_t>(f+24)){
    if(!exact_name(b,f+32,"IsInDialog"))continue;
    const auto at=local_read<int32_t>(f+0x44);
    if(local_read<uint64_t>(f+16)!=(cls|1)||!exact_name(b,local_read<uint64_t>(f+8),"BoolProperty")||
       local_read<int32_t>(f+0x30)!=1||local_read<int32_t>(f+0x34)!=1||local_read<uint32_t>(f+0x70)!=0xff010001U||at<40||at>=local_read<int32_t>(cls+0x58))return 0;
    return npc+at;
   }
  }return 0;
 }
 template<class Pool,class Proof>void command(uint64_t b,uint64_t session,Pool&pool,Packet&p,Proof proof){
  if(!valid(p)||(unknown&&p.mode!=1)||running){p.error=unknown?uncertain:rejected;return;}
  Entry*entry=nullptr;for(auto&e:entries)if(e.request.owner==p.owner){entry=&e;break;}
  if(p.mode){
#if E33_RUNTIME_CINEMATIC_VERSION>=297
   if(!entry||std::memcmp(entry->request.tail,p.tail,56)){p.error=rejected;return;}
#endif
   if(!entry||entry->request.carrier_owner!=p.carrier_owner||std::memcmp(&entry->request.npc,&p.npc,80)||
      std::memcmp(&entry->request.zone,&p.zone,sizeof(p.zone))||std::memcmp(entry->request.leases,p.leases,sizeof(p.leases))){p.error=rejected;return;}
   p.sequence=entry->sequence;p.last_error=entry->last_error;p.elapsed_ms=entry->elapsed;
#if E33_RUNTIME_CINEMATIC_VERSION>=296
   if(p.tail[0])std::memcpy(p.tail+8,&entry->first_seen,8);
#endif
   p.state=entry->state;
   if(p.mode==2){entry->request.owner=0;p.state=3;
#if E33_RUNTIME_CINEMATIC_VERSION>=297
    if(!has_direct()&&!detach_direct()){unknown=true;p.error=uncertain;}
#endif
   }return;
  }
  if(entry||!proof(p.carrier_owner,p.npc)||!call_identity(b,p.world)||!call_identity(b,p.system)||!call_identity(b,p.end)){p.error=rejected;return;}
  const CallIdentity ids[]={p.zone.table,p.zone.function,p.zone.target,p.zone.gi,p.zone.player,p.end};
  for(unsigned i=0;i<6;++i)if(!pool.owns_object(session,p.leases[i],ids[i].address)){p.error=rejected;return;}
  e33_dialogue_text::Dispatcher helper;
  if(helper.world(b,p.npc.address)!=p.world.address||helper.world(b,p.system.address)!=p.world.address||
     !helper.schema(b,p.end.address,2)||zone_ref(b,p.zone.player.address,"PlayerController")!=p.zone.controller.address){p.error=rejected;return;}
  auto check=p.zone;zone_travel(b,check);if(check.error||check.outcome!=1){p.error=rejected;p.last_error=check.error;return;}
  for(auto&e:entries)if(!e.active()){entry=&e;break;}
  if(!entry){p.error=rejected;return;}
#if E33_RUNTIME_CINEMATIC_VERSION>=297
  if(p.tail[1]){
   CallIdentity fn{};uint64_t lease=0;std::memcpy(&fn,p.tail+32,16);std::memcpy(&lease,p.tail+48,8);
   if(!pool.owns_object(session,lease,fn.address)||!attach_direct(b,fn)){p.error=rejected;return;}
   carrier_proof=proof;
  }
#endif
  entry->request=p;entry->state=1;entry->sequence=0;entry->last_error=0;entry->elapsed=0;entry->first_seen=0;
  if(!entry->bound(b)){entry->request.owner=0;p.error=rejected;
#if E33_RUNTIME_CINEMATIC_VERSION>=297
   if(!has_direct())detach_direct();
#endif
   return;}p.state=1;
 }
 template<class Pool,class Proof>void poll(uint64_t b,uint64_t session,Pool&pool,Proof proof){
  if(unknown||running)return;
  for(auto&e:entries){
   if(!e.active()||e.state!=1)continue;const auto&p=e.request;
#if E33_RUNTIME_CINEMATIC_VERSION>=297
   if(p.tail[1])continue;
#endif
   if(!e.bound(b)||!call_identity(b,p.world)||!call_identity(b,p.npc)||!call_identity(b,p.system)){e.state=3;continue;}
   // Battles temporarily unpossess the construction pawn. Keep the armed
   // registration paused until its exact participant proof is valid again.
   if(!proof(p.carrier_owner,p.npc))continue;
   const auto flag=talking_slot(b,p.npc.address);if(!flag){e.state=4;e.last_error=rejected;continue;}
   if(!local_read<uint8_t>(flag))continue;
   if(!e.first_seen)e.first_seen=GetTickCount64();
   e33_dialogue_text::Dispatcher helper;
   const auto dialogue=helper.object_field(b,p.npc.address,"SpawnedDialog");
   if(!dialogue||helper.object_field(b,p.system.address,"ActiveDialogue")!=dialogue)continue;
   // Latch before any engine call: double E and subsequent pump messages cannot replay.
   if(!latch(e.state,e.sequence))continue;running=true;
   auto check=p.zone;zone_travel(b,check);
   auto id=call_capture(b,dialogue);TargetStrongReferenceOps refs{b,id};uint64_t token=0;
   if(pool.acquire(refs,session,id.address,token)!=StrongLeaseResult::Ok){e.last_error=uncertain;unknown=true;running=false;return;}
   if(!stabilize_retained_identity(refs,id)){e.last_error=uncertain;unknown=true;running=false;return;}
   e33_dialogue_text::Packet end;end.owner=p.owner^0x504f5254414cULL;if(!end.owner)end.owner=1;
   end.system=p.system;end.dialogue=id;end.function=p.end;end.dialogue_lease=token;end.mode=2;
   helper.run(b,session,pool,end);
   const auto released=pool.release(refs,session,token);
   if(end.error||end.state!=1||released!=StrongLeaseResult::Ok){e.last_error=uncertain;unknown=true;running=false;return;}
   if(check.error||check.outcome!=1){e.last_error=check.error?check.error:rejected;running=false;continue;}
   // Preserve the successful preflight outcome for local transfers, which do
   // not dispatch a zone load below. The original request has outcome zero.
   ZoneTravelPacket travel{};
#if E33_RUNTIME_CINEMATIC_VERSION>=296
   // A preloaded same-world transfer consumes only the owned E dialogue here.
   // Python's already prepared exact-pawn teleport owns the later dispatch.
   if(!handoff_request(p.zone,check,p.tail[0]!=0,travel)){e.last_error=rejected;running=false;continue;}
   if(!p.tail[0])zone_travel(b,travel);
#else
   if(!handoff_request(p.zone,check,false,travel)){e.last_error=rejected;running=false;continue;}
   zone_travel(b,travel);
#endif
   e.last_error=travel.error;e.state=travel.outcome==1&&!travel.error?2U:4U;
   e.elapsed=uint32_t(GetTickCount64()-e.first_seen);running=false;
   if(travel.outcome==2){unknown=true;e.last_error=uncertain;return;}
  }
 }
};
}
