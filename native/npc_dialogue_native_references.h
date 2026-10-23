#pragma once
#include "npc_dialogue_local_references.h"
namespace e33_npc_presentation {
inline bool dialogue_native_references(uint64_t base,const std::array<CallIdentity,4>& functions,
        std::array<uint64_t,15>& references){
    if(!TargetPodSchemaOps{base}.context())return false;
    struct Spec{const char* name;const char* owner;uint16_t size,returned;uint64_t entry;};
    static constexpr Spec specs[]={
        {"Greater_DoubleDouble","KismetMathLibrary",17,16,0x3854040},
        {"IsValidClass","KismetSystemLibrary",9,8,0x3857e20},
        {"Not_PreBool","KismetMathLibrary",2,1,0x386da00},
        {"BooleanAND","KismetMathLibrary",3,2,0x382b8c0}};
    auto candidate=references;
    for(unsigned i=0;i<4;++i){
        const auto& f=functions[i];const auto& s=specs[i];
        if(!call_identity(base,f)||!exact_name(base,f.address+24,s.name)||
           !e33_mesh::named(base,local_read<uint64_t>(f.address+16),"Function","/Script/CoreUObject")||
           !e33_mesh::named(base,local_read<uint64_t>(f.address+32),s.owner,"/Script/Engine")||
           local_read<uint32_t>(f.address+0xb0)!=0x14022403||
           local_read<uint16_t>(f.address+0xb6)!=s.size||
           local_read<uint16_t>(f.address+0xb8)!=s.returned||
           local_read<uint64_t>(f.address+0xd8)!=base+s.entry)return false;
        candidate[11+i]=f.address;
    }
    references=candidate;return true;
}
}
