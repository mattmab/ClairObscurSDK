#pragma once
#include <cstdint>
#include <limits>

namespace e33_battle_completion {
struct Identity {int32_t index=-1,serial=-1;uint64_t address=0;};
inline bool same(const Identity& a,const Identity& b){return a.index==b.index&&a.serial==b.serial&&a.address==b.address;}
inline bool valid(const Identity& a){return a.index>=0&&a.serial>=0&&a.address;}
struct Context {Identity world,controller,source,arena;uint64_t battle=0,private_name=0;};
inline bool same(const Context& a,const Context& b){return same(a.world,b.world)&&same(a.controller,b.controller)&&
    same(a.source,b.source)&&same(a.arena,b.arena)&&a.battle==b.battle&&a.private_name==b.private_name;}
struct Receipt {uint64_t generation=0,battle=0;Identity world,controller,source,arena;uint8_t result=0;};
enum class State:uint32_t {fresh,armed,ready,consumed,revoked,uncertain};
// One owned battle, one authoritative original callback. There is deliberately
// no API accepting an idle snapshot, elapsed time, or inferred victory.
class Journal {
    Context context_{};Receipt receipt_{};uint64_t generation_=0;State state_=State::fresh;
public:
    State state()const{return state_;}
    bool arm(const Context& c,bool native_owned_proof){
        if(state_!=State::fresh||!native_owned_proof||!valid(c.world)||!valid(c.controller)||
           !valid(c.source)||!valid(c.arena)||!c.battle||!c.private_name||
           generation_==(std::numeric_limits<uint64_t>::max)())return false;
        context_=c;++generation_;state_=State::armed;return true;
    }
    bool observe_post(const Context& current,uint64_t private_name,uint8_t result,
                      bool exact_original_returned,bool native_owned_proof){
        if(state_!=State::armed)return false;
        if(!same(current,context_)||!native_owned_proof){state_=State::revoked;return false;}
        if(private_name!=context_.private_name)return false; // unrelated battle
        if(!exact_original_returned){state_=State::uncertain;return false;}
        if(result!=1&&result!=2){state_=State::uncertain;return false;}
        receipt_={generation_,context_.battle,context_.world,context_.controller,context_.source,context_.arena,result};
        state_=State::ready;return true;
    }
    bool take(uint64_t battle,Receipt& out){
        out={};if(state_!=State::ready||battle!=context_.battle)return false;
        out=receipt_;receipt_={};state_=State::consumed;return true;
    }
    void revoke(){receipt_={};state_=State::revoked;}
    void uncertain(){receipt_={};state_=State::uncertain;}
};
}
