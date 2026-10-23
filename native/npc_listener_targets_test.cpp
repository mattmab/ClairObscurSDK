#include "npc_listener_targets.h"
#include <cassert>
#include <iostream>
#include <vector>
using namespace e33_npc_presentation;
struct Identity {int32_t index,serial;uint64_t address;};
static const Identity targets[]={{7,10,0x30000},{8,11,0x40000}};
struct Entry {int32_t index,serial;};
struct Entries {
    std::vector<Entry> values;
    unsigned reads=0;bool fail=false;
    bool read(uint64_t at,int32_t& index,int32_t& serial){
        ++reads;
        if(fail||at<0x20000||(at-0x20000)%16)return false;
        const auto i=size_t((at-0x20000)/16);
        if(i>=values.size())return false;
        index=values[i].index;serial=values[i].serial;return true;
    }
};
int main(){
    Entries entries{{{99,0},{7,10},{8,11},{7,10},{-1,0}}};
    uint32_t total=999,owned=999;unsigned checks=0;
    auto run=[&](uint64_t data,int32_t count,int32_t capacity,const Identity* ids=targets,size_t n=2){
        ++checks;return count_listener_targets(data,count,capacity,ids,n,entries,total,owned);
    };
    assert(run(0x20000,5,5)&&total==5&&owned==3);
    assert(entries.values[0].index==99&&entries.values[0].serial==0); // unrelated stale target preserved
    assert(run(0,0,0)&&total==0&&owned==0);
    for(const auto spec:std::vector<std::vector<int32_t>>{{-1,0},{2,1},{0,8193},{0,-1}}){
        const auto reads=entries.reads;
        assert(!run(0x20000,spec[0],spec[1])&&total==0&&owned==0&&entries.reads==reads);
    }
    assert(!run(0xffff,1,1));assert(!run(0x20001,1,1));
    assert(!run(0x20000,1,1,nullptr));assert(!run(0x20000,1,1,targets,0));
    assert(!run(0x20000,1,1,targets,129));
    Identity duplicates[]={{7,10,0x30000},{7,11,0x40000}};
    assert(!run(0x20000,1,1,duplicates));
    duplicates[1]={8,11,0x30000};assert(!run(0x20000,1,1,duplicates));
    duplicates[1]={8,0,0x40000};assert(!run(0x20000,1,1,duplicates));
    duplicates[1]={-1,11,0x40000};assert(!run(0x20000,1,1,duplicates));
    duplicates[1]={8,11,0xffff};assert(!run(0x20000,1,1,duplicates));
    entries.values[1].serial=9;
    assert(!run(0x20000,2,2)&&total==0&&owned==0); // reused index is a conflict, not absence
    entries.values[1].serial=10;entries.fail=true;
    assert(!run(0x20000,1,1)&&total==0&&owned==0);
    entries.fail=false;assert(!run(0x20000,6,6)); // incomplete read
    assert(run(0x20000,5,8192)&&total==5&&owned==3);
    std::cout<<checks<<" listener target checks passed\n";
}
