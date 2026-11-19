#include "story_identity_protocol.h"
#include <cassert>
using namespace e33_story_identity;
int main(){
    Entry normal{{1,2,3,4},7},zero{},desired{{prefix,5,6,7},stage},other{{prefix,8,9,10},stage};
    std::vector<Entry> before{normal,zero};assert(normalize(before));Entry found{};
    assert(marker(before,found)==0);
    auto after=before;after.push_back(desired);assert(preserves(before,after,desired));
    after[0].value=5;assert(!preserves(before,after,desired));
    after=before;after.push_back(desired);after.push_back(desired);assert(!normalize(after));
    assert(marker(after,found)==-1);after={desired,other};assert(marker(after,found)==-1);
    after={desired};assert(marker(after,found)==1&&same_key(found,desired));
    after[0].value=0;assert(marker(after,found)==-1);
    Packet p{};p.owner=1;p.lease=2;p.guid[0]=prefix;
    for(auto* id:{&p.engine,&p.viewport,&p.world,&p.controller,&p.gi,&p.function})*id={1,2,0x10000};
    Packet read=p;read_marker(read,before);assert(read.state==2&&!read.error);
    read=p;read_marker(read,{desired});assert(read.state==1&&!read.error&&!std::memcmp(read.guid,desired.guid,16));
    read=p;read_marker(read,{desired,other});assert(read.error==rejected&&!read.state&&!std::memcmp(read.guid,p.guid,16));
    auto malformed=desired;malformed.value=0;read=p;read_marker(read,{malformed});assert(read.error==rejected&&!read.state);
    assert(valid(p));p.mode=2;assert(!valid(p));p.mode=0;p.tail[3]=1;assert(!valid(p));
}
