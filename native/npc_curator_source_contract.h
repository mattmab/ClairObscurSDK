#pragma once
#include "npc_dialogue_isolation_contract.h"
namespace e33_npc_presentation {
struct CuratorDialogueSource {
    CallIdentity dialog{};
    std::array<CallIdentity,4> native_functions{};
};
// Source proof only. Kept separate from the live three-class admission list
// until construction, assembly observation and retirement are connected.
inline bool inherited_dialogue_source_contract(uint64_t base,CallIdentity cls,CallIdentity cdo,
        CallIdentity available,CuratorDialogueSource& output){
    if(!TargetPodSchemaOps{base}.context()||!call_identity(base,cls)||!call_is_class(base,cls.address)||
       !call_identity(base,cdo)||!call_identity(base,available)||
       !(local_read<uint32_t>(cdo.address+8)&0x10)||local_read<uint64_t>(cdo.address+16)!=cls.address)return false;
    CuratorDialogueSource observed{};
    observed.dialog=call_capture(base,local_read<uint64_t>(cls.address+0x40));
    if(!call_identity(base,observed.dialog)||
       !e33_mesh::named(base,observed.dialog.address,"BP_jRPG_NPC_Dialog_C","/Game/LevelTools/NPCs/BP_jRPG_NPC_Dialog")||
       local_read<uint64_t>(available.address+32)!=observed.dialog.address)return false;
    const auto data=local_read<uint64_t>(available.address+0x60);
    const auto capacity=local_read<int32_t>(available.address+0x6c);
    if(data<0x10000||local_read<int32_t>(available.address+0x68)!=232||capacity<232||capacity>65536)return false;
    static constexpr unsigned operands[]={11,49,78,107};
    for(unsigned i=0;i<4;++i){
        observed.native_functions[i]=call_capture(base,local_read<uint64_t>(data+operands[i]));
        if(!observed.native_functions[i].address)return false;
    }
    if(!original_dialogue_isolation_contract(base,cdo,observed.dialog,available,observed.native_functions)||
       !call_identity(base,cls)||!call_identity(base,cdo)||
       local_read<uint64_t>(cls.address+0x40)!=observed.dialog.address)return false;
    output=observed;return true;
}
inline bool curator_source_contract(uint64_t base,CallIdentity cls,CallIdentity cdo,
        CallIdentity available,CuratorDialogueSource& output){
    if(!call_identity(base,cls)||!call_identity(base,cdo))return false;
    const bool camp=e33_mesh::named(base,cls.address,"BP_Character_Camp_Curator_C",
        "/Game/Characters/Heros/Camps/BP_Character_Camp_Curator");
    const bool spirit=e33_mesh::named(base,cls.address,"BP_Character_NPC_Curator_C",
        "/Game/Characters/NPCs/Spirits/Curator/BP_Character_NPC_Curator");
    if((!camp&&!spirit)||!e33_mesh::named(base,cdo.address,
        camp?"Default__BP_Character_Camp_Curator_C":"Default__BP_Character_NPC_Curator_C",
        camp?"/Game/Characters/Heros/Camps/BP_Character_Camp_Curator":"/Game/Characters/NPCs/Spirits/Curator/BP_Character_NPC_Curator"))return false;
    return inherited_dialogue_source_contract(base,cls,cdo,available,output);
}
inline bool francois_source_contract(uint64_t base,CallIdentity cls,CallIdentity cdo,
        CallIdentity available,CuratorDialogueSource& output){
#if E33_RUNTIME_CINEMATIC_VERSION >= 168
    if(!call_identity(base,cls)||!call_identity(base,cdo)||
       !e33_mesh::named(base,cls.address,"BP_NPC_FrancoisTheTurtle_C",
           "/Game/Characters/Enemies/Esquies_Nest/Francois/BP_NPC_FrancoisTheTurtle")||
       !e33_mesh::named(base,cdo.address,"Default__BP_NPC_FrancoisTheTurtle_C",
           "/Game/Characters/Enemies/Esquies_Nest/Francois/BP_NPC_FrancoisTheTurtle"))return false;
    return inherited_dialogue_source_contract(base,cls,cdo,available,output);
#else
    (void)base;(void)cls;(void)cdo;(void)available;(void)output;return false;
#endif
}
}
