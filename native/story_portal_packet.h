#pragma once
#include "zone_travel_protocol.h"
namespace e33_story_portal {
inline bool valid_identity(const CallIdentity&id){return id.index>=0&&id.serial>0&&id.address>=0x10000&&id.address<=0x7fffffffffffULL&&!(id.address&7);}
inline bool latch(uint32_t&state,uint32_t&sequence){if(state!=1||sequence)return false;state=4;++sequence;return true;}
inline bool handoff_request(const ZoneTravelPacket& request,const ZoneTravelPacket& checked,bool local,ZoneTravelPacket& out){
 if(!zone_packet_valid(request)||request.operation||checked.error||checked.outcome!=1||checked.operation)return false;
 auto comparison=checked;comparison.outcome=0;
 if(std::memcmp(&comparison,&request,sizeof(request)))return false;
 // A preflight reply is not a dispatch request: its outcome is nonzero.
 // Keep that ACK only when no zone call is needed for a same-world landing.
 out=local?checked:request;
 if(!local)out.operation=1;
 return true;
}
constexpr uint32_t operation=244,rejected=4010,uncertain=4011;
#pragma pack(push,1)
struct Packet {
 uint32_t version=3,op=operation,error=0,state=0;uint64_t owner=0,carrier_owner=0;
 CallIdentity npc{},world{},system{},end{};uint32_t guid[4]{};
 uint32_t mode=0,sequence=0,last_error=0,elapsed_ms=0;
 ZoneTravelPacket zone{};uint64_t leases[6]{};uint8_t tail[20376]{};
};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984,"Story portal packet");
inline bool valid(const Packet&p){
 if(p.version!=3||p.op!=operation||p.error||p.state||!p.owner||!p.carrier_owner||p.mode>2||p.sequence||p.last_error||p.elapsed_ms||
    p.guid[0]!=0xe33c5701U||!zone_packet_valid(p.zone)||p.zone.operation||
    !valid_identity(p.npc)||!valid_identity(p.world)||
    !valid_identity(p.system)||!valid_identity(p.end))return false;
 for(auto token:p.leases)if(!token)return false;
#if E33_RUNTIME_CINEMATIC_VERSION>=296
 if(p.tail[0]>1)return false;
#if E33_RUNTIME_CINEMATIC_VERSION>=297
 if(p.tail[1]>1||(!p.tail[0]&&p.tail[1]))return false;
 if(p.tail[1]){
  CallIdentity interaction{};uint64_t lease=0;
  std::memcpy(&interaction,p.tail+32,16);std::memcpy(&lease,p.tail+48,8);
  if(!valid_identity(interaction)||!lease)return false;
 }
 for(unsigned i=2;i<sizeof(p.tail);++i)
  if(!(p.tail[1]&&i>=32&&i<56)&&p.tail[i])return false;
#else
 for(unsigned i=1;i<sizeof(p.tail);++i)if(p.tail[i])return false;
#endif
#else
 for(auto b:p.tail)if(b)return false;
#endif
 return true;
}
}
