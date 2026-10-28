#pragma once
#include "invocation_protocol.h"
#include <array>
#include <cstddef>

namespace e33_sequencer_array {
constexpr uint32_t operation=220,maximum=128;
#pragma pack(push,1)
struct Output {CallIdentity identity{};uint64_t token=0;};
struct Packet {
    uint32_t version,op,error,state;uint64_t request;
    uint32_t mode,index;CallIdentity target,function,subject;uint64_t subject_token;
    uint32_t total,count,outcome,reserved;Output outputs[maximum];uint8_t tail[17808];
};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984 && offsetof(Packet,outputs)==104);
inline bool zero(const void* p,size_t n) {const auto* b=static_cast<const uint8_t*>(p);for(size_t i=0;i<n;++i)if(b[i])return false;return true;}
inline bool identity(const CallIdentity& id) {return id.index>=0 && id.serial>0 && id.address>=0x10000 && !(id.address&7);}
inline bool request(const Packet& p) {
    return p.version==3 && p.op==operation && !p.error && !p.state && p.request &&
        (p.mode==1 || p.mode==2) && (p.mode==1 ? p.index==0 : p.index<65536) &&
        identity(p.target) && identity(p.function) && identity(p.subject) && p.subject_token &&
        !p.total && !p.count && !p.outcome && !p.reserved && zero(p.outputs,sizeof(p.outputs)) && zero(p.tail,sizeof(p.tail));
}
struct Array {uint64_t data=0;int32_t count=0,capacity=0;};
static_assert(sizeof(Array)==16);
enum class Result {ok,rejected,range,unknown};

// Durable return allocation. Captured outputs move into the containing session's
// normal lease pool before array storage is freed; only pointer-free rows publish.
class Frame {
    alignas(16) uint8_t arguments_[24]{};
    std::array<Output,maximum> outputs_{};uint32_t count_=0,total_=0;
    enum State {idle,dispatching,returned,retaining,freeing,complete,uncertain} state_=idle;
public:
    bool available() const {return state_==idle;}
    bool quarantined() const {return state_!=idle && state_!=complete;}
    uint32_t count() const {return state_==complete ? count_ : 0;}
    uint32_t total() const {return state_==complete ? total_ : 0;}
    const Output* outputs() const {return state_==complete ? outputs_.data() : nullptr;}
    template<class Ops> Result query(Ops& ops,const Packet& p) {
        if(!available() || !request(p) || !ops.validate() || !ops.preflight(p.mode==1 ? maximum : 1))return Result::rejected;
        const auto at=p.mode==1 ? 8U : 0U;
        if(p.mode==1)std::memcpy(arguments_,&p.subject.address,8);
        state_=dispatching;ops.dispatch(arguments_);state_=returned;
        if(!ops.validate() || (p.mode==1 && std::memcmp(arguments_,&p.subject.address,8)) ||
           (p.mode==2 && !zero(arguments_+16,8))) {state_=uncertain;return Result::unknown;}
        Array array{};std::memcpy(&array,arguments_+at,16);
        if(array.count<0 || array.count>65536 || array.capacity<array.count || array.capacity>131072 ||
           (array.capacity && (!array.data || (array.data&7))) || (!array.capacity && array.data) ||
           array.data>UINT64_MAX-uint64_t(array.capacity)*8) {state_=uncertain;return Result::unknown;}
        total_=uint32_t(array.count);
        const bool out_of_range=p.mode==1 ? total_>maximum : p.index>=total_;
        const auto count=out_of_range ? 0U : p.mode==1 ? total_ : 1U;
        for(uint32_t i=0;i<count;++i) {
            const auto source=p.mode==1 ? i : p.index;
            uint64_t object=0;auto& row=outputs_[i];
            if(!ops.read_pointer(array.data+uint64_t(source)*8,object) || !object || !ops.capture(object,row.identity)) {
                state_=uncertain;return Result::unknown;
            }
            for(uint32_t j=0;j<i;++j)if(row.identity.address==outputs_[j].identity.address){state_=uncertain;return Result::unknown;}
            state_=retaining;
            if(!ops.retain(row.identity,row.token) || !row.token){state_=uncertain;return Result::unknown;}
            ++count_;state_=returned;
        }
        if(!ops.validate() || std::memcmp(arguments_+at,&array,16)){state_=uncertain;return Result::unknown;}
        if(array.data){state_=freeing;ops.free_array(array.data);}
        std::memset(arguments_,0,sizeof(arguments_));state_=complete;
        return out_of_range ? Result::range : Result::ok;
    }
    bool reset() {
        if(!available() && state_!=complete)return false;
        std::memset(arguments_,0,sizeof(arguments_));outputs_={};count_=total_=0;state_=idle;return true;
    }
};
}
