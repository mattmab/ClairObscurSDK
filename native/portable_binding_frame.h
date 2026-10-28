#pragma once
#include "invocation_protocol.h"
#include <cstring>
namespace e33_portable_binding {
constexpr uint32_t operation=222,packet_size=20984;
#pragma pack(push,1)
struct Packet {
    uint32_t version,operation,error,state;uint64_t request,reserved;
    CallIdentity target,function,root,destination,source;
    uint64_t tokens[5];int32_t guid[4];uint8_t binding[24];uint32_t outcome;
    uint8_t padding[packet_size-196];
};
#pragma pack(pop)
static_assert(sizeof(Packet)==packet_size);
inline bool request(const Packet& p){
    if(p.version!=3||p.operation!=operation||p.error||p.state||!p.request||p.reserved||p.outcome)return false;
    const CallIdentity ids[]={p.target,p.function,p.root,p.destination,p.source};
    for(unsigned i=0;i<5;++i)if(ids[i].index<0||ids[i].serial<=0||ids[i].address<0x10000||ids[i].address%8||!p.tokens[i])return false;
    bool guid=false;for(auto word:p.guid)guid=guid||word!=0;
    for(auto byte:p.binding)if(byte)return false;
    for(auto byte:p.padding)if(byte)return false;
    return guid;
}
enum class Result {Rejected,Complete,Unavailable,Unknown};
class Frame {
    struct Arguments {uint64_t root,destination;int32_t guid[4];uint64_t source;uint8_t result[24];};
    static_assert(sizeof(Arguments)==64);
    alignas(16) Arguments args_{};
    enum State {Idle,Dispatching,Complete,Uncertain} state_=Idle;
public:
    bool quarantined()const{return state_==Dispatching||state_==Uncertain;}
    bool available()const{return state_==Idle;}
    template<class Ops> Result query(Ops& ops,const Packet& p){
        if(!available()||!request(p)||!ops.validate())return Result::Rejected;
        args_.root=p.root.address;args_.destination=p.destination.address;args_.source=p.source.address;
        std::memcpy(args_.guid,p.guid,16);uint8_t before[40]{};std::memcpy(before,&args_,40);
        state_=Dispatching;ops.dispatch(&args_);
        if(!ops.validate()||std::memcmp(before,&args_,40)){state_=Uncertain;return Result::Unknown;}
        bool nonzero=false;for(unsigned i=0;i<16;++i)nonzero=nonzero||args_.result[i]!=0;
        if(nonzero&&std::memcmp(args_.result,p.guid,16)){state_=Uncertain;return Result::Unknown;}
        state_=Complete;return nonzero?Result::Complete:Result::Unavailable;
    }
    const uint8_t* result()const{return state_==Complete?args_.result:nullptr;}
    void reset(){if(state_==Complete){args_={};state_=Idle;}}
};
}
