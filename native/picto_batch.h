#pragma once
#include "picto_batch_protocol.h"
// The exact GetFrameCount exec thunk, observed through live reflection, reads
// this engine counter. Never substitute elapsed time or message count for it.
inline bool picto_frame_source(uint64_t base) {
 constexpr uint8_t code[]={0x48,0x8b,0x42,0x20,0x33,0xc9,0x48,0x85,0xc0,0x0f,0x95,0xc1,0x48,0x03,0xc8,0x48,0x89,0x4a,0x20,0x48,0x8b,0x05,0x26,0x4c,0xa2,0x05,0x49,0x89,0x00,0xc3};
 return !std::memcmp(reinterpret_cast<void*>(base+0x384e0d0),code,sizeof(code));
}
struct PictoBatch {
 PictoBatchPacket job{};
 uint64_t owner=0,last_frame=0,started=0;
 UINT_PTR timer=0;
 bool active() const {return job.state==1;}
 void stop(uint32_t state=3,uint32_t error=0) {
  if(active()){job.state=state;job.error=error;}
  if(timer){KillTimer(nullptr,timer);timer=0;}
 }
 void command(uint64_t base,uint64_t requested_owner,PictoBatchPacket& p) {
  if(!valid_picto_batch(p)){p.error=1770;return;}
  const auto operation=p.operation;
  if(operation==1) {
   if(active() || (job.token && job.token==p.token)){p.error=1771;return;}
   if(!picto_frame_source(base)){p.error=1772;return;}
   job=p;owner=requested_owner;last_frame=local_read<uint64_t>(base+0x9272d10);started=GetTickCount64();
   job.state=p.count?1:2;
   if(active()) {timer=SetTimer(nullptr,0,USER_TIMER_MINIMUM,nullptr);if(!timer)stop(4,1773);}
  } else {
   if(job.token!=p.token || owner!=requested_owner){p.error=1774;return;}
   if(operation==3)stop();
  }
  p=job;p.operation=operation;
 }
 void tick(uint64_t base,bool context_valid) {
  if(!active())return;
  if(!context_valid || GetTickCount64()-started>60000 || !picto_frame_source(base)){stop(4,1775);return;}
  const auto frame=local_read<uint64_t>(base+0x9272d10);
  if(frame==last_frame)return;
  if(frame<last_frame){stop(4,1775);return;}
  last_frame=frame;
  auto& entry=job.entries[job.processed];
  PictoProgressionPacket p{};p.operation=10;p.target=job.manager;p.function=job.function;
  p.source=entry.asset;p.panel=job.table;p.game_instance=job.game_instance;
  p.expected=job.desired?0:1;p.value=static_cast<int32_t>(job.desired);
  // Existing production guards and stock game calls remain authoritative.
  if(job.desired==2) {
   p={};p.operation=4;p.target=entry.asset;p.function=job.function;p.value=static_cast<int32_t>(job.reserved);
   picto_batch_level(base,job.manager,p);
  } else if(job.desired==3) {
   p={};p.operation=5;p.target=job.manager;p.function=job.function;p.source=entry.asset;p.game_instance=job.game_instance;
   picto_batch_mastery(base,job.table,job.reserved!=0,p);
  } else picto_inventory(base,p);
  entry.error=p.error;entry.outcome=p.outcome;entry.frame=frame;
  ++job.processed;
  if(job.processed==job.count)stop(2);
 }
};
