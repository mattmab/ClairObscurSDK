#pragma once
#include "invocation_protocol.h"
#include <cstring>
namespace e33_metadata {
constexpr uint32_t Action=137,Capacity=128;
enum Outcome:uint32_t{NotDispatched=0,RetainedStable=1,Unknown=2};
#pragma pack(push,1)
struct Row{CallIdentity before,after;uint64_t token;uint32_t error,outcome;};
struct Packet{uint32_t version,count,error,completed,active,failed;Row rows[Capacity];};
#pragma pack(pop)
static_assert(sizeof(Packet)==6168,"Metadata stabilization ABI");
inline bool same(const CallIdentity&a,const CallIdentity&b){return a.index==b.index&&a.serial==b.serial&&a.address==b.address;}
inline bool zero(const CallIdentity&a){return !a.index&&!a.serial&&!a.address;}
inline bool valid(const Packet&p){
 if(p.version!=1||!p.count||p.count>Capacity||p.error||p.completed||p.active||p.failed)return false;
 for(unsigned i=0;i<Capacity;++i){const auto&r=p.rows[i];
  if(i>=p.count){if(!zero(r.before)||!zero(r.after)||r.token||r.error||r.outcome)return false;continue;}
  if(r.before.index<0||r.before.serial<0||r.before.address<0x10000||(r.before.address&7)||!zero(r.after)||r.token||r.error||r.outcome)return false;
  for(unsigned j=0;j<i;++j)if(r.before.index==p.rows[j].before.index||r.before.address==p.rows[j].before.address)return false;
 }return true;
}
}
