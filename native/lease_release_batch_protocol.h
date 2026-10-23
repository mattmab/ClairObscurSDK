#pragma once
#include <cstdint>
#include <cstring>
namespace e33_lease_batch {
constexpr uint32_t Action=136,Capacity=128;
enum Outcome:uint32_t {NotDispatched=0,Released=1,Deferred=2,Rejected=3,Unknown=4};
#pragma pack(push,1)
struct Row {uint64_t token;uint32_t error,outcome;};
struct Packet {uint32_t version,count,error,completed,active,failed;Row rows[Capacity];};
#pragma pack(pop)
static_assert(sizeof(Packet)==2072,"Lease batch ABI");
inline bool valid(const Packet& p){
    if(p.version!=1||!p.count||p.count>Capacity||p.error||p.completed||p.active||p.failed)return false;
    for(unsigned i=0;i<Capacity;++i){
        const auto& row=p.rows[i];
        if(i>=p.count){if(row.token||row.error||row.outcome)return false;continue;}
        if(!row.token||row.error||row.outcome)return false;
        for(unsigned j=0;j<i;++j)if(row.token==p.rows[j].token)return false;
    }
    return true;
}
}
