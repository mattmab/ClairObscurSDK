#pragma once
#include "invocation_protocol.h"
#include <vector>
#include <algorithm>
namespace e33_story_identity {
constexpr uint32_t operation=231,rejected=3880,uncertain=3881,prefix=0xe33c5701U;
constexpr int32_t stage=0x53335031;
struct Entry {uint32_t guid[4]{};int32_t value=0;};
inline bool same_key(const Entry&a,const Entry&b){return !std::memcmp(a.guid,b.guid,16);}
inline bool less(const Entry&a,const Entry&b){
    for(unsigned i=0;i<4;++i)if(a.guid[i]!=b.guid[i])return a.guid[i]<b.guid[i];
    return false;
}
inline bool normalize(std::vector<Entry>& entries){
    std::sort(entries.begin(),entries.end(),less);
    for(size_t i=1;i<entries.size();++i)if(same_key(entries[i-1],entries[i]))return false;
    return true;
}
inline int marker(const std::vector<Entry>& entries,Entry& result){
    int found=0;
    for(const auto&e:entries)if(e.guid[0]==prefix){
        if(e.value!=stage||++found>1)return -1;
        result=e;
    }
    return found;
}
inline bool preserves(const std::vector<Entry>& before,std::vector<Entry> after,const Entry& added){
    if(after.size()!=before.size()+1||!normalize(after))return false;
    const auto at=std::find_if(after.begin(),after.end(),[&](const Entry&e){return same_key(e,added)&&e.value==added.value;});
    if(at==after.end())return false;
    after.erase(at);
    for(size_t i=0;i<before.size();++i)if(!same_key(before[i],after[i])||before[i].value!=after[i].value)return false;
    return true;
}
#pragma pack(push,1)
struct Packet {
    uint32_t version=3,op=operation,error=0,state=0;uint64_t owner=0;
    CallIdentity engine{},viewport{},world{},controller{},gi{},function{};
    uint64_t lease=0;uint32_t guid[4]{};uint32_t mode=0,reserved=0;
    uint8_t tail[20832]{};
};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984,"Story identity packet");
// Complete a validated read without accepting a caller-supplied identity as truth.
inline void read_marker(Packet& p,const std::vector<Entry>& entries){
    Entry existing{};const int found=marker(entries,existing);
    if(found<0){p.error=rejected;return;}
    if(found)std::memcpy(p.guid,existing.guid,16);
    p.state=found?1U:2U;
}
inline bool identity(const CallIdentity&id){return id.index>=0&&id.serial>=0&&id.address>=0x10000&&id.address<=0x7fffffffffffULL&&!(id.address&7);}
inline bool valid(const Packet&p){
    if(p.version!=3||p.op!=operation||p.error||p.state||!p.owner||!p.lease||p.mode>1||p.reserved||p.guid[0]!=prefix)return false;
    for(const auto*id:{&p.engine,&p.viewport,&p.world,&p.controller,&p.gi,&p.function})if(!identity(*id))return false;
    for(auto b:p.tail)if(b)return false;
    return true;
}
}
