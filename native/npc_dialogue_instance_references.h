#pragma once
#include "npc_dialogue_local_references.h"
#include "picto_progression.h"
namespace e33_npc_presentation {
// Exact read-only descriptors referenced by the inherited availability body.
// No property values are changed and no dialogue function is invoked here.
inline bool dialogue_instance_references(uint64_t base,CallIdentity actor,CallIdentity dialog,
        std::array<uint64_t,15>& references){
    if(!TargetPodSchemaOps{base}.context()||!call_identity(base,actor)||!call_identity(base,dialog)||
       !call_is_class(base,dialog.address)||
       !e33_mesh::named(base,dialog.address,"BP_jRPG_NPC_Dialog_C","/Game/LevelTools/NPCs/BP_jRPG_NPC_Dialog")||
       !call_derives(base,local_read<uint64_t>(actor.address+16),dialog.address))return false;
    struct Spec{const char* name;const char* type;int offset,width;uint64_t table,flags;};
    static constexpr Spec specs[]={
        {"InteractionRadius","DoubleProperty",1720,8,0x6e11788,0x9001040000205ULL},
        {"DialogueToPlay","ClassProperty",2080,8,0x6e12ac8,0x8001000000205ULL},
        {"IsInDialog","BoolProperty",2168,1,0x6e119b0,0x8001040010205ULL},
        {"CanBeInteractedWith","BoolProperty",2288,1,0x6e119b0,0x8001040010205ULL}};
    auto candidate=references;
    const auto extent=local_read<int32_t>(local_read<uint64_t>(actor.address+16)+0x58);
    if(extent<2289||extent>16777216)return false;
    for(unsigned i=0;i<4;++i){
        const auto& s=specs[i];uint64_t field=0;
        if(!picto_field(base,actor.address,s.name,s.type,s.offset,s.width,&field)||
           local_read<uint64_t>(field)!=base+s.table||local_read<uint64_t>(field+0x38)!=s.flags)return false;
        const auto owner=local_read<uint64_t>(field+16)&~uint64_t(1);
        if(i?owner!=dialog.address:
           !e33_mesh::named(base,owner,"BP_jRPG_NPC_Base_C","/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_NPC_Base"))return false;
        if(i>=2&&local_read<uint32_t>(field+0x70)!=0xff010001)return false;
        candidate[7+i]=field;
    }
    if(!call_identity(base,actor)||!call_identity(base,dialog))return false;
    references=candidate;return true;
}
}
