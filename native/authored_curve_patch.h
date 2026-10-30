#pragma once
#include "invocation_protocol.h"
#include <vector>
#include <cmath>
#include <cstring>
#include <limits>
#include <cstddef>

namespace e33_curve_patch {
// Shipping numeric channels derive from this reflected base. Validate that
// exact parent rather than treating every inherited channel as unsupported.
template<class Ops> bool channel_base(const Ops& ops,uint64_t type){
    const auto parent=ops.template read<uint64_t>(type+64);
    return ops.struct_type(parent)&&ops.named(parent,"MovieSceneChannel","/Script/MovieScene")&&
        ops.template read<uint32_t>(parent+88)==80&&!ops.template read<uint64_t>(parent+64)&&
        !ops.template read<uint64_t>(parent+80);
}
constexpr uint32_t operation=226,maximum_edits=64,maximum_keys=65536;
enum Kind:uint32_t {Boolean=1,Byte=2,Integer=3,Float=4,Double=5};
#pragma pack(push,1)
struct Selector {char field[64]{};uint32_t element=0,reserved=0;};
struct Edit {uint32_t index=0;int32_t before_time=0,after_time=0;uint32_t reserved=0;uint64_t before=0,after=0;};
struct Packet {
    uint32_t version=3,op=operation,error=0,state=0;uint64_t request=0;
    CallIdentity source{},target{},sequence{},outer{};uint64_t tokens[4]{};
    int32_t signature[4]{};
    uint32_t kind=0,depth=0,key_count=0,edit_count=0,outcome=0,reserved=0;
    Selector path[16]{};Edit edits[maximum_edits]{};uint8_t tail[17624]{};
};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984 && offsetof(Packet,path)==160 && offsetof(Packet,edits)==1312);
inline bool zero(const void* value,size_t size){const auto* p=static_cast<const uint8_t*>(value);for(size_t i=0;i<size;++i)if(p[i])return false;return true;}
inline bool identity(const CallIdentity& id){return id.index>=0&&id.serial>0&&id.address>=0x10000&&id.address<=0x7fffffffffffULL&&!(id.address&7);}
inline unsigned width(uint32_t kind){return kind==Double?8U:kind==Integer||kind==Float?4U:kind==Boolean||kind==Byte?1U:0U;}
inline unsigned stride(uint32_t kind){return kind==Float?28U:kind==Double?32U:width(kind);}
inline bool number(uint32_t kind,uint64_t bits){
    const auto size=width(kind);if(!size||(size<8&&(bits>>(size*8))))return false;
    if(kind==Boolean)return bits<=1;
    if(kind==Float){float value=0;std::memcpy(&value,&bits,4);return std::isfinite(value);}
    if(kind==Double){double value=0;std::memcpy(&value,&bits,8);return std::isfinite(value);}
    return true;
}
inline bool request(const Packet& p){
    if(p.version!=3||p.op!=operation||p.error||p.state||!p.request||p.outcome||p.reserved||
       !identity(p.source)||!identity(p.target)||!identity(p.sequence)||!identity(p.outer)||
       p.source.address==p.target.address||!p.depth||p.depth>16||!p.key_count||p.key_count>maximum_keys||
       !p.edit_count||p.edit_count>maximum_edits||!width(p.kind)||zero(p.signature,16)||!zero(p.tail,sizeof(p.tail)))return false;
    for(auto token:p.tokens)if(!token)return false;
    for(unsigned i=0;i<16;++i){
        const auto& item=p.path[i];
        if(i>=p.depth){if(!zero(&item,sizeof(item)))return false;continue;}
        if(!item.field[0]||item.field[63]||item.reserved||(item.element!=UINT32_MAX&&item.element>=64))return false;
        for(unsigned j=0;item.field[j];++j){const auto c=static_cast<unsigned char>(item.field[j]);if(c<32||c>=127)return false;}
        const auto n=std::strlen(item.field);if(!zero(item.field+n+1,63-n))return false;
    }
    for(unsigned i=0;i<maximum_edits;++i){
        const auto& edit=p.edits[i];
        if(i>=p.edit_count){if(!zero(&edit,sizeof(edit)))return false;continue;}
        if(edit.index>=p.key_count||edit.reserved||(i&&edit.index<=p.edits[i-1].index)||!number(p.kind,edit.before)||!number(p.kind,edit.after))return false;
    }
    return true;
}
struct Storage {
    uint64_t source_times=0,source_values=0,target_times=0,target_values=0;
    uint32_t count=0,kind=0;
    bool operator==(const Storage& b)const{return source_times==b.source_times&&source_values==b.source_values&&target_times==b.target_times&&target_values==b.target_values&&count==b.count&&kind==b.kind;}
};
inline bool disjoint(uint64_t a,uint64_t n,uint64_t b,uint64_t m){return a>=0x10000&&b>=0x10000&&a<=UINT64_MAX-n&&b<=UINT64_MAX-m&&(a+n<=b||b+m<=a);}
inline bool shape(const Storage& s,const Packet& p){
    if(s.count!=p.key_count||s.kind!=p.kind)return false;
    const uint64_t sizes[]={uint64_t(s.count)*4,uint64_t(s.count)*stride(s.kind),uint64_t(s.count)*4,uint64_t(s.count)*stride(s.kind)};
    const uint64_t pointers[]={s.source_times,s.source_values,s.target_times,s.target_values};
    for(unsigned i=0;i<4;++i){if(pointers[i]&(i%2?width(s.kind)-1:3))return false;for(unsigned j=0;j<i;++j)if(!disjoint(pointers[i],sizes[i],pointers[j],sizes[j]))return false;}
    return true;
}
enum class Result {Rejected,Applied,Unknown};

// The containing target adapter verifies the exact reflected storage, source
// signature, private copy ownership and construction-only admission. This frame
// owns all pre-write observations through post-write verification and SEH.
class Frame {
    enum State {Idle,Writing,Complete,Uncertain} state_=Idle;
    Storage storage_{};uint64_t tokens_[4]{};
    std::vector<int32_t> times_,after_times_;
    std::vector<uint8_t> values_,after_values_;
    void discard(){times_.clear();after_times_.clear();values_.clear();after_values_.clear();}
public:
    bool quarantined()const{return state_==Writing||state_==Uncertain;}
    bool protects(uint64_t token)const{if(quarantined())for(auto held:tokens_)if(token==held)return true;return false;}
    bool reset(){if(quarantined())return false;state_=Idle;discard();std::memset(tokens_,0,sizeof(tokens_));return true;}
    template<class Ops> Result patch(Ops& ops,const Packet& p){
        if(state_!=Idle||!request(p))return Result::Rejected;
        Storage observed{};
        if(!ops.resolve(p,observed)||!shape(observed,p))return Result::Rejected;
        storage_=observed;
        times_.resize(p.key_count);values_.resize(size_t(p.key_count)*stride(p.kind));
        if(!ops.read(observed.source_times,times_.data(),times_.size()*4)||
           !ops.read(observed.source_values,values_.data(),values_.size())||
           !ops.equal(observed.target_times,times_.data(),times_.size()*4)||
           !ops.equal(observed.target_values,values_.data(),values_.size())){discard();return Result::Rejected;}
        for(unsigned i=0;i<p.key_count;++i){
            uint64_t bits=0;std::memcpy(&bits,values_.data()+size_t(i)*stride(p.kind),width(p.kind));
            if(!number(p.kind,bits)||(i&&times_[i]<=times_[i-1])){discard();return Result::Rejected;}
        }
        after_times_=times_;after_values_=values_;
        for(unsigned i=0;i<p.edit_count;++i){
            const auto& edit=p.edits[i];uint64_t before=0;
            std::memcpy(&before,values_.data()+size_t(edit.index)*stride(p.kind),width(p.kind));
            if(times_[edit.index]!=edit.before_time||before!=edit.before){discard();return Result::Rejected;}
            after_times_[edit.index]=edit.after_time;
            std::memcpy(after_values_.data()+size_t(edit.index)*stride(p.kind),&edit.after,width(p.kind));
        }
        for(unsigned i=1;i<p.key_count;++i)if(after_times_[i]<=after_times_[i-1]){discard();return Result::Rejected;}
        Storage current{};
        if(!ops.resolve(p,current)||!(current==storage_)||!ops.equal(current.source_times,times_.data(),times_.size()*4)||
           !ops.equal(current.source_values,values_.data(),values_.size())||!ops.equal(current.target_times,times_.data(),times_.size()*4)||
           !ops.equal(current.target_values,values_.data(),values_.size())){discard();return Result::Rejected;}
        std::memcpy(tokens_,p.tokens,sizeof(tokens_));state_=Writing;
        for(unsigned i=0;i<p.edit_count;++i){
            const auto& edit=p.edits[i];
            if(!ops.write(current.target_times+uint64_t(edit.index)*4,&edit.after_time,4)||
               !ops.write(current.target_values+uint64_t(edit.index)*stride(p.kind),&edit.after,width(p.kind))){state_=Uncertain;return Result::Unknown;}
        }
        Storage final{};
        if(!ops.resolve(p,final)||!(final==storage_)||!ops.equal(final.source_times,times_.data(),times_.size()*4)||
           !ops.equal(final.source_values,values_.data(),values_.size())||!ops.equal(final.target_times,after_times_.data(),after_times_.size()*4)||
           !ops.equal(final.target_values,after_values_.data(),after_values_.size())){state_=Uncertain;return Result::Unknown;}
        state_=Complete;return Result::Applied;
    }
};
}
