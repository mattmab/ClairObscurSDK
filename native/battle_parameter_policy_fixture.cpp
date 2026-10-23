#include "battle_parameter_policy.h"
#include <cassert>
using namespace e33_enemy_spawn;
struct Ops {
    bool valid=true,verified=true,corrupt_presentation=false;
    ParameterCall clear=ParameterCall::Completed;
    unsigned clears=0,checks=0;
    bool preflight(void*,const ParameterPolicy&){++checks;return valid;}
    ParameterCall clear_party(void* frame){
        ++clears;if(clear!=ParameterCall::Completed)return clear;
        auto* bytes=static_cast<uint8_t*>(frame);std::memset(bytes+200,0,16);
        if(corrupt_presentation)bytes[224]=0;
        return ParameterCall::Completed;
    }
    bool verify(void*,const ParameterPolicy&){return verified;}
};
int main(){
    assert(supported_party_slot_layout(9,4,12,0x8001040000200ULL));
    assert(!supported_party_slot_layout(12,4,12,0x8001040000200ULL));
    assert(!supported_party_slot_layout(9,4,9,0x8001040000200ULL));
    assert(!supported_party_slot_layout(9,8,16,0x8001040000200ULL));
    assert(!supported_party_slot_layout(9,4,12,0));
    for(const auto mode:{ParameterPolicyMode::OriginalParameters,ParameterPolicyMode::Isolated,ParameterPolicyMode::AuthoredParty}){
        std::array<uint8_t,344> frame;frame.fill(0x55);frame[224]=1;const auto before=frame;
        Ops ops;const ParameterPolicy policy{mode,0x123400000005ULL};
        assert(apply_parameter_policy(ops,frame.data(),policy)==ParameterCall::Completed);
        uint64_t name=0;std::memcpy(&name,frame.data()+16,8);assert(name==policy.instance_name);
        assert(frame[224]==1);assert(ops.clears==(mode==ParameterPolicyMode::Isolated?1U:0U));
        for(size_t i=0;i<344;++i){const bool changed=(i>=16&&i<24)||(mode!=ParameterPolicyMode::OriginalParameters&&(i>=168&&i<192))||(mode==ParameterPolicyMode::Isolated&&(i>=200&&i<216));if(!changed)assert(frame[i]==before[i]);}
        if(mode!=ParameterPolicyMode::OriginalParameters){for(size_t i=168;i<192;++i)assert(frame[i]==0);}else assert(frame[168]==0x55);
        if(mode==ParameterPolicyMode::AuthoredParty)assert(!std::memcmp(frame.data()+200,before.data()+200,16));
    }
    {std::array<uint8_t,344> frame{};Ops o;o.valid=false;assert(apply_parameter_policy(o,frame.data(),{ParameterPolicyMode::Isolated,5})==ParameterCall::NotDispatched);assert(o.clears==0);}
    for(const auto outcome:{ParameterCall::NotDispatched,ParameterCall::Unknown}){std::array<uint8_t,344> frame;frame.fill(0x55);const auto before=frame;Ops o;o.clear=outcome;assert(apply_parameter_policy(o,frame.data(),{ParameterPolicyMode::Isolated,5})==outcome);assert(frame==before);}
    {std::array<uint8_t,344> frame;frame.fill(0x55);frame[224]=1;Ops o;o.corrupt_presentation=true;assert(apply_parameter_policy(o,frame.data(),{ParameterPolicyMode::Isolated,5})==ParameterCall::Unknown);}
    {std::array<uint8_t,344> frame{};Ops o;o.verified=false;assert(apply_parameter_policy(o,frame.data(),{ParameterPolicyMode::OriginalParameters,5})==ParameterCall::Unknown);}
    {std::array<uint8_t,344> frame{};Ops o;assert(apply_parameter_policy(o,frame.data(),{ParameterPolicyMode(9),5})==ParameterCall::NotDispatched);assert(apply_parameter_policy(o,frame.data(),{ParameterPolicyMode::Isolated,0})==ParameterCall::NotDispatched);assert(o.checks==0);}
    return 0;
}
