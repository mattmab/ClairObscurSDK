#pragma once
#include "invocation_protocol.h"
#include <cstring>
namespace e33_story_participants {
constexpr uint32_t operation=233,capacity=256,rejected=3900,uncertain=3901;
#pragma pack(push,1)
struct Participant {uint64_t owner=0,lease=0;CallIdentity actor{};};
struct Packet {
 uint32_t version=3,op=operation,error=0,state=0;
 uint64_t nonce=0,dialogue_lease=0;
 CallIdentity system{},dialogue{},update_actors{};
 uint32_t mode=0,count=0;
 Participant participants[capacity]{};uint8_t tail[12704]{};
};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984,"Dialogue participant packet");
inline bool identity(const CallIdentity& id){return id.index>=0&&id.serial>0&&id.address>=0x10000&&id.address<=0x7fffffffffffULL&&!(id.address&7);}
inline bool same(const CallIdentity& a,const CallIdentity& b){return !std::memcmp(&a,&b,sizeof(a));}
inline bool valid(const Packet& p){
 if(p.version!=3||p.op!=operation||p.error||p.state||!p.nonce||!p.dialogue_lease||p.mode>1||
    !p.count||p.count>capacity||!identity(p.system)||!identity(p.dialogue)||!identity(p.update_actors))return false;
 for(uint32_t i=0;i<capacity;++i){
  const auto& row=p.participants[i];
  if(i>=p.count){if(row.owner||row.lease||row.actor.index||row.actor.serial||row.actor.address)return false;continue;}
  if(!row.owner||!row.lease||!identity(row.actor))return false;
  for(uint32_t j=0;j<i;++j){const auto& other=p.participants[j];
   if(row.owner==other.owner||row.lease==other.lease||row.actor.index==other.actor.index||row.actor.address==other.actor.address)return false;
  }
 }
 for(auto byte:p.tail)if(byte)return false;
 return true;
}
// Engine array allocation/copy stays in the target adapter. This only computes
// a bounded value list, preserving original slots and their order.
struct List {uint64_t values[capacity+2]{};uint32_t count=0;};
inline bool contains(const List& list,uint64_t value){for(uint32_t i=0;i<list.count;++i)if(list.values[i]==value)return true;return false;}
inline bool append(List& list,uint64_t value){
 if(!value||list.count>capacity+2)return false;
 if(contains(list,value))return true;
 if(list.count==capacity+2)return false;
 list.values[list.count++]=value;
 return true;
}
inline bool compose(const List& current,const List& participants,uint64_t owner,uint64_t player,bool remove,List& result){
 if(&result==&current||&result==&participants||current.count>capacity+2||participants.count>capacity||!owner||!player)return false;
 List next{};
 for(uint32_t i=0;i<current.count;++i){
  const auto value=current.values[i];
  if(!value)return false;
  // Cleanup removes only registered custom slots, retaining native owner/player.
  if(remove&&value!=owner&&value!=player&&contains(participants,value))continue;
  if(next.count>=capacity+2)return false;
  next.values[next.count++]=value;
 }
 if(!remove){
  for(uint32_t i=0;i<participants.count;++i)if(!append(next,participants.values[i]))return false;
 }
 result=next;return true;
}
}
