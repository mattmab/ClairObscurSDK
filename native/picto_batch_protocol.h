#pragma once
#include "picto_progression_protocol.h"
constexpr uint32_t SessionPictoBatch=122;
constexpr uint32_t PictoBatchCapacity=342;
#pragma pack(push,1)
struct PictoBatchEntry {
 CallIdentity asset{};uint32_t error=0,outcome=0;uint64_t frame=0;
};
struct PictoBatchPacket {
 uint32_t version=1,operation=0,error=0,state=0;
 uint64_t token=0;
 uint32_t count=0,desired=0,processed=0,reserved=0;
 CallIdentity manager{},function{},table{},game_instance{};
 PictoBatchEntry entries[PictoBatchCapacity]{};
};
#pragma pack(pop)
static_assert(sizeof(PictoBatchPacket)==11048);
inline bool valid_picto_batch(const PictoBatchPacket& p) {
 if(p.version!=1 || p.operation<1 || p.operation>3 || !p.token || p.error || p.state || p.processed || p.desired>3 || p.count>PictoBatchCapacity)return false;
 // desired=2: owned-item level in reserved; desired=3: mastered boolean in reserved.
 if(p.desired==2 ? (p.reserved<1 || p.reserved>33) : p.desired==3 ? p.reserved>1 : p.reserved!=0)return false;
 const CallIdentity ids[]={p.manager,p.function,p.table,p.game_instance};
 for(const auto& id:ids) {
  if(p.operation==1 ? (id.index<0 || !id.address) : (id.index || id.serial || id.address))return false;
 }
 if(p.operation!=1 && (p.count || p.desired))return false;
 for(uint32_t i=0;i<PictoBatchCapacity;++i) {
  const auto& e=p.entries[i];if(e.error || e.outcome || e.frame)return false;
  if(i<p.count) {
   if(e.asset.index<0 || !e.asset.address)return false;
   for(uint32_t j=0;j<i;++j)if(e.asset.address==p.entries[j].asset.address)return false;
  } else if(e.asset.index || e.asset.serial || e.asset.address)return false;
 }
 return true;
}
