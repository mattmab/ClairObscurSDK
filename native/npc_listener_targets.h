#pragma once
#include <cstddef>
#include <cstdint>
namespace e33_npc_presentation {
// Shared read-only storage predicate. EntryOps supplies observations, never
// mutation. Retained identities may outlive original component destruction.
template<class Identity,class EntryOps> bool count_listener_targets(
        uint64_t data,int32_t count,int32_t capacity,const Identity* targets,
        size_t target_count,EntryOps& entries,uint32_t& total,uint32_t& owned){
    total=0;owned=0;
    if(!targets||!target_count||target_count>128||count<0||capacity<count||capacity>8192||
       (count&&(data<0x10000||(data&7))))return false;
    for(size_t i=0;i<target_count;++i){
        if(targets[i].index<0||targets[i].serial<=0||targets[i].address<0x10000)return false;
        for(size_t j=0;j<i;++j)if(targets[j].index==targets[i].index||targets[j].address==targets[i].address)return false;
    }
    uint32_t matched=0;
    for(int32_t i=0;i<count;++i){
        int32_t index=0,serial=0;
        if(!entries.read(data+uint64_t(i)*16,index,serial))return false;
        for(size_t t=0;t<target_count;++t)if(index==targets[t].index){
            if(serial!=targets[t].serial)return false;
            ++matched;break;
        }
    }
    total=uint32_t(count);owned=matched;return true;
}
}
