#pragma once
#include "owned_text_value.h"

// Session-owned input for audited native dialogue Text[] entry points. The
// engine receives a borrowed TArray view and copies its FText elements. This
// is not a general mutable-array codec and is never serialized as pointers.
namespace e33_dialogue_text {
constexpr uint32_t capacity=16;
struct Input {const uint16_t* units=nullptr;uint32_t count=0;};
enum class State {Empty,Preparing,Ready,DispatchUnknown,Returned,Cleaned,Quarantined};
struct Frame {
    OwnedTextStorage owners[capacity];
    TargetTextValue elements[capacity]{};
    TargetStringValue array{}; // TArray header layout, elements are FText.
    uint32_t count=0;
    State state=State::Empty;
    Frame()=default;
    Frame(const Frame&)=delete;
    Frame& operator=(const Frame&)=delete;

    template<class Ops> bool prepare(Ops& ops,const Input* inputs,uint32_t size) {
        if(state!=State::Empty||!inputs||!size||size>capacity)return false;
        for(uint32_t i=0;i<size;++i)if(!valid_text_units(inputs[i].units,inputs[i].count))return false;
        count=size;state=State::Preparing;
        for(uint32_t i=0;i<count;++i){
            if(create_owned_text(ops,owners[i],inputs[i].units,inputs[i].count)!=OwnedTextResult::Ok)return false;
            // Non-owning bitwise view. owners[] remains the only owner.
            elements[i]=owners[i].value;
        }
        array={reinterpret_cast<uint64_t>(elements),static_cast<int32_t>(count),static_cast<int32_t>(count)};
        state=State::Ready;return true;
    }
    template<class Ops> bool begin(Ops& ops) {
        if(state!=State::Ready||!ops.can_create())return false;
        for(uint32_t i=0;i<count;++i)if(owners[i].state!=OwnedTextState::Live||!ops.known_text(owners[i].value))return false;
        state=State::DispatchUnknown;return true;
    }
    bool returned() {
        if(state!=State::DispatchUnknown)return false;
        bool unchanged=array.data==reinterpret_cast<uint64_t>(elements)&&array.count==static_cast<int32_t>(count)&&array.capacity==static_cast<int32_t>(count);
        for(uint32_t i=0;i<count;++i)unchanged=unchanged&&!std::memcmp(&elements[i],&owners[i].value,sizeof(TargetTextValue));
        if(!unchanged){state=State::Quarantined;return false;}
        state=State::Returned;return true;
    }
    template<class Ops> bool cleanup(Ops& ops) {
        if(state==State::DispatchUnknown||state==State::Quarantined)return false;
        if(state==State::Empty||state==State::Cleaned)return true;
        bool deferred=false;
        for(uint32_t i=count;i>0;--i){
            auto result=release_owned_text(ops,owners[i-1]);
            if(result==OwnedTextResult::ReleaseDeferred)deferred=true;
            else if(result!=OwnedTextResult::Ok){state=State::Quarantined;return false;}
        }
        if(deferred)return false;
        std::memset(elements,0,sizeof(elements));array={};state=State::Cleaned;return true;
    }
};
}
