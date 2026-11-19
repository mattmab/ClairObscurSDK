#pragma once
#include <cstdint>
#include <cstddef>
#include <cstring>
#include <algorithm>

// Collision-only visibility for an existing owned map. No actor discovery,
// material changes, collision writes, or authority over foreign actors.
namespace e33_map_visibility {
constexpr uint32_t operation=262,capacity=32,rejected=2116,uncertain=2117;
constexpr size_t packet_size=20984;
struct Identity {int32_t index,serial;uint64_t address;};
static_assert(sizeof(Identity)==16);
template<class T> T read(const uint8_t* p){T value{};std::memcpy(&value,p,sizeof(value));return value;}
inline bool valid_identity(Identity id){return id.index>=0&&id.serial>0&&id.address>=0x10000&&!(id.address&7);}
inline bool same(Identity a,Identity b){return a.index==b.index&&a.serial==b.serial&&a.address==b.address;}
inline bool empty(const uint8_t* first,const uint8_t* last){return std::all_of(first,last,[](uint8_t v){return v==0;});}
inline bool valid(const uint8_t* raw,size_t size){
    if(size!=packet_size||read<uint32_t>(raw)!=3||read<uint32_t>(raw+4)!=operation||
       read<uint32_t>(raw+8)||read<uint32_t>(raw+12)||!read<uint64_t>(raw+16)||
       !empty(raw+24,raw+88)||!valid_identity(read<Identity>(raw+88))||!empty(raw+104,raw+2000))return false;
    const auto count=read<uint32_t>(raw+2000);
    if(!count||count>capacity||!empty(raw+2004,raw+4096)||!empty(raw+4096+16*count,raw+size))return false;
    for(uint32_t i=0;i<count;++i){const auto id=read<Identity>(raw+4096+16*i);
        if(!valid_identity(id))return false;
        for(uint32_t j=0;j<i;++j)if(same(id,read<Identity>(raw+4096+16*j)))return false;
    }
    return true;
}
struct Result {uint32_t error=0,completed=0;bool quarantine=false;};
template<class Ops> Result run(Ops& ops,uint32_t count){
    Result out{};
    if(!count||count>capacity||!ops.function()){out.error=rejected;return out;}
    // Prove the whole bounded request before the first visibility change.
    for(uint32_t i=0;i<count;++i){bool hidden=false;
        if(!ops.current()||!ops.observe(i,hidden)){out.error=rejected;return out;}}
    bool attempted=false;
    auto fail=[&](){out.quarantine=attempted||out.completed!=0;out.error=out.quarantine?uncertain:rejected;return out;};
    for(uint32_t i=0;i<count;++i){bool hidden=false;
        if(!ops.current()||!ops.observe(i,hidden))return fail();
        if(!hidden){attempted=true;if(!ops.hide(i))return fail();}
        if(!ops.current()||!ops.observe(i,hidden)||!hidden)return fail();
        ++out.completed;
        if(ops.budget_exhausted())break;
    }
    return out;
}
}
