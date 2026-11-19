#pragma once
#include "blueprint_call_protocol.h"
constexpr uint32_t kDialogueSlotVersion=12;
inline uint32_t validate_dialogue_slot_call(const CallPacket&p){
 if(p.version!=kDialogueSlotVersion||p.entry_rva!=0x33a3bc0||p.function_flags!=67240963||
    p.parameter_size!=48||p.allocation_extent!=48||p.return_offset!=40||p.field_count!=9)return 1480;
 const char*names[]={"Asset","SlotNodeName","BlendInTime","BlendOutTime","InPlayRate","LoopCount","BlendOutTriggerTime","InTimeToStartMontageAt","ReturnValue"};
 const uint32_t kinds[]={CallObject,kBlueprintNameKind,CallFloat,CallFloat,CallFloat,CallInt32,CallFloat,CallFloat,CallObject};
 const uint32_t offsets[]={0,8,16,20,24,28,32,36,40};
 for(unsigned i=0;i<9;++i)if(!std::memchr(p.fields[i].name,0,96)||std::strcmp(p.fields[i].name,names[i])||p.fields[i].kind!=kinds[i]||p.fields[i].offset!=offsets[i]||p.fields[i].dimension!=1)return 1480;
 const auto&f=p.fields[1];
 if(!std::memchr(f.name,0,96))return 1480;
 const auto slot=f.name+std::strlen(f.name)+1;
 if(slot>=f.name+96||!std::memchr(slot,0,size_t(f.name+96-slot))||
    (std::strcmp(slot,"DefaultSlot")&&std::strcmp(slot,"Mouth")))return 1480;
 float values[6]{};std::memcpy(values,p.data+16,24);int loops=0;std::memcpy(&loops,p.data+28,4);
 if(!((values[0]==.4f&&values[1]==.4f)||(values[0]==.35f&&values[1]==.35f))||values[2]!=1.f||
    (loops!=1&&loops!=10000)||values[4]!=-1.f||values[5]!=0.f)return 1480;
 auto normalized=p;normalized.version=kBlueprintCallVersion;normalized.function_flags=0;normalized.entry_rva=kBlueprintThunkRva;
 return validate_blueprint_call(normalized);
}
