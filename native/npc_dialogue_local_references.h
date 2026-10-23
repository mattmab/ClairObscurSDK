#pragma once
#include "mesh_owner.h"
#include "npc_dialogue_local_schema.h"
#include <array>
namespace e33_npc_presentation {
// Resolve only the seven original locals of the observed dialogue function.
// This is not spawn authority: instance fields and native calls are separate gates.
inline bool dialogue_local_references(uint64_t base,CallIdentity available,
        std::array<uint64_t,15>& references){
    if(!TargetPodSchemaOps{base}.context()||!call_identity(base,available)||
       !exact_name(base,available.address+24,"IsInteractionAvailable"))return false;
    static constexpr const char* names[]={"Available","CallFunc_Greater_DoubleDouble_ReturnValue",
        "CallFunc_IsValidClass_ReturnValue","CallFunc_Not_PreBool_ReturnValue",
        "CallFunc_BooleanAND_ReturnValue","CallFunc_BooleanAND_ReturnValue","CallFunc_BooleanAND_ReturnValue"};
    static constexpr unsigned slots[]={6,0,1,2,3,4,5};
    const auto first=local_read<uint64_t>(available.address+0x50);
    auto field=first;auto candidate=references;
    for(unsigned i=0;i<7;++i){
        if(field<0x10000)return false;
        const DialogueLocalSchema schema{local_read<uint64_t>(field),local_read<uint64_t>(field+16),
            local_read<uint64_t>(field+0x38),local_read<uint32_t>(field+36),
            local_read<uint32_t>(field+0x30),local_read<uint32_t>(field+0x34),
            local_read<uint32_t>(field+0x44),local_read<uint32_t>(field+0x70)};
        if(!dialogue_local_schema(schema,i,base,available.address)||
           !exact_name(base,local_read<uint64_t>(field+8),"BoolProperty"))return false;
        // Compare the exact base FName without conflating numbered locals.
        uint64_t unnumbered=local_read<uint32_t>(field+32);
        if(!exact_name(base,reinterpret_cast<uint64_t>(&unnumbered),names[i]))return false;
        candidate[slots[i]]=field;field=local_read<uint64_t>(field+24);
    }
    if(field||!call_identity(base,available)||local_read<uint64_t>(available.address+0x50)!=first)return false;
    references=candidate;return true;
}
}
