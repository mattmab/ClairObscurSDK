#include <cstdint>
#include <cstring>
#include <vector>
#include <cassert>
#include <cstdio>
#include "picto_batch_protocol.h"
using UINT_PTR=uintptr_t;
constexpr unsigned USER_TIMER_MINIMUM=10;
static uint64_t test_frame=100,now=0;
static unsigned calls=0,kills=0;
static bool timer_fail=false;
uint64_t GetTickCount64(){return now;}
UINT_PTR SetTimer(void*,UINT_PTR,unsigned,void*){return timer_fail?0:1;}
bool KillTimer(void*,UINT_PTR){++kills;return true;}
template<class T>T local_read(uint64_t){return static_cast<T>(test_frame);}
void picto_inventory(uint64_t,PictoProgressionPacket& p){
 ++calls;assert(p.operation==10 && p.expected==1 && p.value==0);
 if(p.source.index==11)p.error=1759;else {p.outcome=1;p.observed=0;}
}
void picto_batch_level(uint64_t,const CallIdentity& system,PictoProgressionPacket& p){
 ++calls;assert(system.address==16 && p.operation==4 && p.value==32);
 if(p.target.index==11)p.error=1777;else {p.outcome=1;p.observed=32;}
}
void picto_batch_mastery(uint64_t,const CallIdentity& table,bool mastered,PictoProgressionPacket& p){
 ++calls;assert(table.address==16 && p.operation==5 && p.target.address==16 && p.game_instance.address==16);
 if(p.source.index==11)p.error=1777;else {p.outcome=1;p.observed=mastered?4:0;}
}
#include "picto_batch.h"
static PictoBatchPacket request(uint64_t token=1){
 PictoBatchPacket p{};p.operation=1;p.token=token;p.count=3;
 p.manager=p.function=p.table=p.game_instance={1,1,16};
 for(int i=0;i<3;++i)p.entries[i].asset={10+i,1,uint64_t(160+i*16)};
 return p;
}
int main(){
 std::vector<uint8_t> memory(0x384e100);
 constexpr uint8_t code[]={0x48,0x8b,0x42,0x20,0x33,0xc9,0x48,0x85,0xc0,0x0f,0x95,0xc1,0x48,0x03,0xc8,0x48,0x89,0x4a,0x20,0x48,0x8b,0x05,0x26,0x4c,0xa2,0x05,0x49,0x89,0x00,0xc3};
 std::memcpy(memory.data()+0x384e0d0,code,sizeof(code));const auto base=reinterpret_cast<uint64_t>(memory.data());
 PictoBatch batch;auto p=request();assert(valid_picto_batch(p));batch.command(base,7,p);assert(p.state==1);
 batch.tick(base,true);assert(calls==0);
 ++test_frame;batch.tick(base,true);batch.tick(base,true);assert(calls==1);
 ++test_frame;batch.tick(base,true);assert(calls==2 && batch.job.entries[1].error==1759);
 ++test_frame;batch.tick(base,true);assert(calls==3 && batch.job.state==2 && kills==1);
 assert(batch.job.entries[0].frame<batch.job.entries[1].frame && batch.job.entries[1].frame<batch.job.entries[2].frame);
 p=request(2);batch.command(base,7,p);++test_frame;batch.tick(base,true);assert(calls==4);
 PictoBatchPacket cancel{};cancel.operation=3;cancel.token=2;batch.command(base,8,cancel);assert(cancel.error==1774 && batch.active());
 cancel={};cancel.operation=3;cancel.token=2;batch.command(base,7,cancel);assert(cancel.state==3);++test_frame;batch.tick(base,true);assert(calls==4);
 p=request(3);batch.command(base,7,p);++test_frame;batch.tick(base,false);assert(!batch.active() && calls==4 && batch.job.error==1775);
 p=request(4);batch.command(base,7,p);now=60001;++test_frame;batch.tick(base,true);assert(calls==4 && !batch.active());
 p=request(5);p.entries[1].asset=p.entries[0].asset;assert(!valid_picto_batch(p));
 p=request(6);timer_fail=true;batch.command(base,7,p);assert(p.error==1773 && !batch.active());
 p=request(7);timer_fail=false;p.desired=2;p.reserved=32;assert(valid_picto_batch(p));batch.command(base,7,p);
 const auto before=calls;++test_frame;batch.tick(base,true);batch.tick(base,true);assert(calls==before+1);
 ++test_frame;batch.tick(base,true);++test_frame;batch.tick(base,true);
 assert(batch.job.state==2 && batch.job.entries[1].error==1777 && calls==before+3);
 p=request(8);p.desired=2;assert(!valid_picto_batch(p));p.reserved=34;assert(!valid_picto_batch(p));
 for(unsigned mastered=0;mastered<=1;++mastered) {
  p=request(10+mastered);p.desired=3;p.reserved=mastered;assert(valid_picto_batch(p));batch.command(base,7,p);
  const auto previous=calls;
  for(int i=0;i<3;++i){++test_frame;batch.tick(base,true);batch.tick(base,true);assert(calls==previous+unsigned(i)+1);}
  assert(batch.job.state==2 && batch.job.entries[1].error==1777);
 }
 p=request(12);p.desired=3;p.reserved=2;assert(!valid_picto_batch(p));
 p=request(9);memory[0x384e0d0]=0;batch.command(base,7,p);assert(p.error==1772);
 std::puts("Picto frame batch: frame gate, cancellation, protection, owner, lifetime, timeout, packet and source guards PASS");
}
