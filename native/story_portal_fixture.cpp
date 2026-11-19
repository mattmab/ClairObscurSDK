#include <cassert>
#include <cstdio>
#include <cstring>
#include "story_portal_packet.h"
int main(){
 using namespace e33_story_portal;Packet p;p.owner=1;p.carrier_owner=2;
 p.npc={1,2,0x10000};p.world={2,3,0x20000};p.system={3,4,0x30000};p.end={4,5,0x40000};p.guid[0]=0xe33c5701;
 p.zone.version=2;p.zone.operation=0;
 const CallIdentity id={1,2,0x10000};p.zone.table=p.zone.function=p.zone.target=p.zone.gi=p.zone.player=p.zone.controller=id;
 strcpy_s(p.zone.level,"Lumiere");strcpy_s(p.zone.asset,"Level_Lumiere_Main_V2");strcpy_s(p.zone.tag,"Level.SpawnPoint.LumiereAct03.Opera");
 for(auto&t:p.leases)t=3;
 assert(valid(p));auto changed=p;changed.guid[0]=1;assert(!valid(changed));
 auto checked=p.zone;checked.outcome=1;ZoneTravelPacket dispatch{};
 assert(!zone_packet_valid(checked)); // Reusing this reply caused error 1800.
 assert(handoff_request(p.zone,checked,false,dispatch));
 assert(zone_packet_valid(dispatch)&&dispatch.operation==1&&dispatch.outcome==0);
 assert(!std::memcmp(&dispatch.table,&p.zone.table,sizeof(p.zone)-16));
 assert(handoff_request(p.zone,checked,true,dispatch));
 assert(dispatch.operation==0&&dispatch.outcome==1);
 checked.error=1801;assert(!handoff_request(p.zone,checked,false,dispatch));
 checked.error=0;checked.controller.address+=8;assert(!handoff_request(p.zone,checked,false,dispatch));
 changed=p;changed.zone.operation=1;assert(!valid(changed));changed=p;changed.tail[0]=1;
#if E33_RUNTIME_CINEMATIC_VERSION>=296
 assert(valid(changed));changed.tail[0]=2;assert(!valid(changed));changed=p;changed.tail[1]=1;assert(!valid(changed));
#if E33_RUNTIME_CINEMATIC_VERSION>=297
 changed=p;changed.tail[0]=changed.tail[1]=1;
 const CallIdentity interaction={9,10,0x90000};const uint64_t interaction_lease=11;
 std::memcpy(changed.tail+32,&interaction,16);std::memcpy(changed.tail+48,&interaction_lease,8);
 assert(valid(changed));changed.tail[56]=1;assert(!valid(changed));changed.tail[56]=0;
 changed.tail[0]=0;assert(!valid(changed));changed.tail[0]=1;
 std::memset(changed.tail+48,0,8);assert(!valid(changed));
#endif
#else
 assert(!valid(changed));
#endif
 changed=p;changed.sequence=1;assert(!valid(changed));changed=p;changed.npc.serial=0;assert(!valid(changed));
 uint32_t state=1,sequence=0;assert(latch(state,sequence));assert(state==4&&sequence==1);
 for(unsigned i=0;i<10;++i)assert(!latch(state,sequence));assert(sequence==1);
 state=2;assert(!latch(state,sequence));state=4;assert(!latch(state,sequence));
 std::puts("Portal bounds, save namespace, validation-only setup and exactly-once latch passed");
}

