#pragma once
#include "npc_original_admission.h"
#include "npc_curator_source_contract.h"
namespace e33_npc_presentation {
inline bool presentation_class_contract(uint64_t base,CallIdentity cls,CallIdentity cdo,CallIdentity available){
    if(original_class(base,cls))return original_class_contract(base,cls,cdo,available);
    CuratorDialogueSource source{};
    return curator_source_contract(base,cls,cdo,available,source)||francois_source_contract(base,cls,cdo,available,source);
}
}
