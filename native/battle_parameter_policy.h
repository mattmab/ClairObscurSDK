#pragma once
#include "battle_parameter_frame.h"
#include <cstring>
namespace e33_enemy_spawn {
enum class ParameterPolicyMode:uint32_t { OriginalParameters=0, Isolated=1, AuthoredParty=2 };
struct ParameterPolicy {ParameterPolicyMode mode;uint64_t instance_name;};
inline bool supported_party_slot_layout(uint32_t declared_size,uint32_t alignment,uint32_t stride,uint64_t flags) {
    return declared_size==9&&alignment==4&&stride==12&&flags==0x8001040000200ULL&&
        ((declared_size+alignment-1)&~(alignment-1))==stride;
}

// Called only through the persistent frame's once-only mutation journal.
// Ops proves retained source/struct, exact property schemas and authority for
// an existing owned actor's unique FName. No name-pool insertion is permitted.
template<class Ops> ParameterCall apply_parameter_policy(Ops& ops,void* frame,const ParameterPolicy& policy) {
    if(!frame||!policy.instance_name||
       (policy.mode!=ParameterPolicyMode::OriginalParameters&&policy.mode!=ParameterPolicyMode::Isolated&&policy.mode!=ParameterPolicyMode::AuthoredParty)||
       !ops.preflight(frame,policy))return ParameterCall::NotDispatched;
    std::array<uint8_t,344> before{};std::memcpy(before.data(),frame,before.size());
    const bool isolated=policy.mode!=ParameterPolicyMode::OriginalParameters;
    const bool clear_party=policy.mode==ParameterPolicyMode::Isolated;
    if(clear_party){
        const auto cleared=ops.clear_party(frame);
        if(cleared!=ParameterCall::Completed)return cleared;
    }
    auto* bytes=static_cast<uint8_t*>(frame);
    // These are verified FName and UObject-reference POD fields, not owned
    // FString/array/map storage. Container clearing stays with the engine.
    std::memcpy(bytes+16,&policy.instance_name,8);
    if(isolated)std::memset(bytes+168,0,24);
    for(size_t at=0;at<before.size();++at){
        const bool writable=(at>=16&&at<24)||(isolated&&(at>=168&&at<192))||(clear_party&&(at>=200&&at<216));
        if(!writable&&bytes[at]!=before[at])return ParameterCall::Unknown;
    }
    return ops.verify(frame,policy)?ParameterCall::Completed:ParameterCall::Unknown;
}
}
