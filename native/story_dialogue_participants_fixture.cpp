#include "story_dialogue_participants.h"
#include <cassert>
#include <cstdio>
int main(){
 using namespace e33_story_participants;
 List native{},custom{},result{},restored{};
 native.values[0]=10;native.values[1]=20;native.values[2]=30;native.count=3;
 custom.values[0]=10;custom.values[1]=40;custom.values[2]=50;custom.count=3;
 assert(compose(native,custom,10,20,false,result));assert(result.count==5);
 for(unsigned i=0;i<3;++i)assert(result.values[i]==native.values[i]);
 assert(compose(result,custom,10,20,true,restored));assert(restored.count==3);
 for(unsigned i=0;i<3;++i)assert(restored.values[i]==native.values[i]);
 assert(!compose(native,custom,10,20,false,native));
 List full{};full.count=capacity+2;for(unsigned i=0;i<full.count;++i)full.values[i]=100+i;
 List duplicates{};duplicates.count=1;duplicates.values[0]=full.values[0];
 assert(compose(full,duplicates,10,20,false,result));assert(result.count==capacity+2);
 result.count=99;assert(!compose(full,custom,10,20,false,result));assert(result.count==99);
 Packet p;p.nonce=1;p.dialogue_lease=2;p.system={1,1001,0x10000};p.dialogue={2,1002,0x20000};p.update_actors={3,1003,0x30000};
 p.count=2;p.participants[0]={3,4,{4,1004,0x40000}};p.participants[1]={5,6,{5,1005,0x50000}};assert(valid(p));
 p.participants[1].actor.index=4;assert(!valid(p));p.participants[1].actor.index=5;
 p.participants[1].owner=3;assert(!valid(p));p.participants[1].owner=5;
 p.participants[2].lease=9;assert(!valid(p));p.participants[2].lease=0;
 p.mode=1;assert(valid(p));p.mode=2;assert(!valid(p));p.mode=0;
 p.tail[12703]=1;assert(!valid(p));
 std::puts("Dialogue participant validation, merge and cleanup policy passed");
}
