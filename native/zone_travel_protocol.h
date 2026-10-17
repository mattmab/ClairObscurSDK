#pragma once
#include "invocation_protocol.h"
constexpr uint32_t SessionZoneTravel=132;
#pragma pack(push,1)
struct ZoneTravelPacket {
 uint32_t version, operation, outcome, error;
 CallIdentity table, function, target, gi, player, controller;
 char level[96], asset[96], tag[128];
};
#pragma pack(pop)
static_assert(sizeof(ZoneTravelPacket)==432);
inline bool zone_text(const char* p,size_t n) {
 if(!p[0] || p[n-1])return false;
 bool end=false;
 for(size_t i=0;i<n;++i){const auto c=static_cast<unsigned char>(p[i]);if(!c)end=true;else if(end || !((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_'||c=='.'))return false;}
 return true;
}
inline bool zone_packet_valid(const ZoneTravelPacket& p) {
 if(p.version!=1 || p.operation>1 || p.outcome || p.error || !zone_text(p.level,96) || !zone_text(p.asset,96) || !zone_text(p.tag,128))return false;
 const CallIdentity* identities[]={&p.table,&p.function,&p.target,&p.gi,&p.player,&p.controller}; for(const auto* id:identities)if(id->index<0 || id->serial<0 || !id->address)return false;
 return true;
}
