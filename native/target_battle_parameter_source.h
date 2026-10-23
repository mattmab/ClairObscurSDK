#pragma once
#include "battle_parameter_source_match.h"
#include "target_pod_schema.h"
#include "numbered_field_name.h"
namespace e33_enemy_spawn {
struct TargetParameterSourceProof {
    uint64_t base;
    bool valid(uint64_t object)const{return TargetPodSchemaOps{base}.identity(call_capture(base,object));}
    bool name(uint64_t object,const char* expected,uint32_t number)const {
        return exact_field_name(base,object+24,expected,number);
    }
    uint64_t outer(uint64_t object)const{return local_read<uint64_t>(object+32);}
    static bool allowed(void* context,const CallIdentity& root,const CallIdentity& source) {
        if(!context)return false;
        auto& proof=*static_cast<TargetParameterSourceProof*>(context);
        if(!TargetPodSchemaOps{proof.base}.context()||!TargetPodSchemaOps{proof.base}.identity(root)||
           !TargetPodSchemaOps{proof.base}.identity(source))return false;
        return match_parameter_source(proof,root.address,source.address,parameter_source_profiles,
            sizeof(parameter_source_profiles)/sizeof(parameter_source_profiles[0]));
    }
};
}
