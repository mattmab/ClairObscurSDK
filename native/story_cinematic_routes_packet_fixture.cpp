#include <cstdint>
#include <cassert>
#include <cstddef>
#include <iostream>
struct CallIdentity{int32_t index=0,serial=0;uint64_t address=0;};
#include "story_cinematic_routes_packet.h"
using namespace e33_story_cinematics;
Packet request(uint32_t routes){
 Packet p;p.owner=42;p.route_count=routes;
 for(unsigned i=0;i<active_count(p);++i){p.ids[i]={int32_t(i+1),2,0x10000+8ULL*i};p.leases[i]=i+1;}
 p.nkeys=1;p.keys[0][0]=0xe33c5701U;return p;
}
int main(){
 static_assert(offsetof(Packet,route_count)==1492);
 for(uint32_t routes:{1U,3U,5U}){
  for(uint32_t mode:{0U,1U,2U,4U}){auto p=request(routes);p.mode=mode;assert(valid_bounds(p));}
  auto p=request(routes);p.mode=3;p.choices=2;p.selected=p.target=1;
  p.menu[0]={40,4,0x20000};p.menu[1]={41,4,0x30000};assert(valid_bounds(p));
  p.selected=2;assert(!valid_bounds(p));p.selected=1;p.menu[0].serial=0;assert(!valid_bounds(p));
 }
 for(uint32_t count_bad:{0U,6U}){auto p=request(1);p.route_count=count_bad;assert(!valid_bounds(p));}
 auto p=request(1);p.ids[8]={20,4,0x20000};assert(!valid_bounds(p));
 p=request(1);p.leases[8]=42;assert(!valid_bounds(p));
 p=request(1);p.leases[0]=0;assert(!valid_bounds(p));
 p=request(1);p.tail[0]=1;assert(!valid_bounds(p));
 p=request(1);p.keys[0][0]=0;assert(!valid_bounds(p));
 p=request(1);p.keys[1][0]=0xe33c5701U;assert(!valid_bounds(p));
 p=request(1);p.routed=1;assert(!valid_bounds(p));
 p=request(1);p.choices=1;assert(!valid_bounds(p));
 std::cout<<"Cinematic route count, ownership, menu and padding checks passed\n";
}
