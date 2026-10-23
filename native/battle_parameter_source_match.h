#pragma once
#include "battle_parameter_source_profiles.h"
#include <cstddef>
namespace e33_enemy_spawn {
template<class Ops> bool match_parameter_source(Ops& ops,uint64_t root,uint64_t source,
    const ParameterSourceProfile* profiles,size_t count) {
    if(!root||!source||root==source||!profiles||!count||count>46)return false;
    unsigned matches=0;
    for(size_t row=0;row<count;++row){
        const auto& profile=profiles[row];
        if(profile.count<2||profile.count>8)return false;
        auto object=source;bool matched=true;
        for(uint32_t at=0;at<profile.count;++at){
            const auto& name=profile.chain[at];
            if(!object||!ops.valid(object)||!ops.name(object,name.base,name.number)||
               ((at+1==profile.count)!=(object==root))){matched=false;break;}
            object=ops.outer(object);
        }
        if(matched&&object&&ops.valid(object)&&ops.name(object,profile.package,0)&&!ops.outer(object))++matches;
    }
    return matches==1;
}
}
