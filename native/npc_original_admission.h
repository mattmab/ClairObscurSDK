#pragma once
#include "mesh_owner.h"
#include "npc_unavailable_body.h"
namespace e33_npc_presentation {
struct OriginalClass {const char* name;const char* package;const char* cdo;};
inline const OriginalClass* original_class(uint64_t base,const CallIdentity& observed){
    static constexpr OriginalClass classes[]={
        {"BP_JRPG_NPC_Dialog_NPC_MirrorAlicia_NoInteract_C","/Game/Characters/Enemies/HumanEnnemies/Alicia/BP_JRPG_NPC_Dialog_NPC_MirrorAlicia_NoInteract","Default__BP_JRPG_NPC_Dialog_NPC_MirrorAlicia_NoInteract_C"},
        {"BP_JRPG_NPC_Dialog_NPC_MirrorClea_NoInteract_C","/Game/Characters/Enemies/HumanEnnemies/Clea_v1/BP_JRPG_NPC_Dialog_NPC_MirrorClea_NoInteract","Default__BP_JRPG_NPC_Dialog_NPC_MirrorClea_NoInteract_C"},
        {"BP_JRPG_NPC_Dialog_NPC_RealRenoir_NoInteract_C","/Game/Characters/Enemies/HumanEnnemies/Real_Renoir/BP_JRPG_NPC_Dialog_NPC_RealRenoir_NoInteract","Default__BP_JRPG_NPC_Dialog_NPC_RealRenoir_NoInteract_C"}};
    if(!call_identity(base,observed)||!call_is_class(base,observed.address))return nullptr;
    for(const auto& item:classes)if(e33_mesh::named(base,observed.address,item.name,item.package))return &item;
    return nullptr;
}
inline bool original_class_contract(uint64_t base,CallIdentity cls,CallIdentity cdo,CallIdentity available){
    if(!TargetPodSchemaOps{base}.context())return false;
    const auto recipe=original_class(base,cls);
    if(!recipe||!call_identity(base,cdo)||!call_identity(base,available)||
       !e33_mesh::named(base,cdo.address,recipe->cdo,recipe->package)||
       !(local_read<uint32_t>(cdo.address+8)&0x10)||local_read<uint64_t>(cdo.address+16)!=cls.address||
       local_read<uint64_t>(available.address+32)!=cls.address||!exact_name(base,available.address+24,"IsInteractionAvailable")||
       local_read<uint32_t>(available.address+0xb0)!=0xc420000||local_read<uint16_t>(available.address+0xb6)!=1||
       local_read<uint16_t>(available.address+0xb8)!=65535||local_read<int32_t>(available.address+0x58)!=1||
       local_read<uint64_t>(available.address+0xd8)!=base+0x13937a0)return false;
    const auto field=local_read<uint64_t>(available.address+0x50);
    if(!field||local_read<uint64_t>(field)!=base+0x6e119b0||local_read<uint64_t>(field+16)!=(available.address|1)||
       !exact_name(base,field+32,"Available")||local_read<int32_t>(field+0x30)!=1||local_read<int32_t>(field+0x34)!=1||
       local_read<int32_t>(field+0x44)!=0||local_read<uint64_t>(field+0x38)!=0x8001040000380ULL||
       local_read<uint32_t>(field+0x70)!=0xff010001||local_read<uint64_t>(field+24))return false;
    const auto data=local_read<uint64_t>(available.address+0x60);
    const auto count=local_read<int32_t>(available.address+0x68),capacity=local_read<int32_t>(available.address+0x6c);
    if(data<0x10000||count!=14||capacity<count||capacity>65536)return false;
    uint8_t bytes[14]{};std::memcpy(bytes,reinterpret_cast<const void*>(data),14);
    return constant_unavailable_body(bytes,14,field)&&call_identity(base,cls)&&call_identity(base,cdo)&&call_identity(base,available)&&
        local_read<uint64_t>(available.address+0x60)==data&&local_read<int32_t>(available.address+0x68)==14;
}
}
