#pragma once
#include "picto_stable_profile.h"
// Session-bound exact observed scripts. A new game process requires fresh research.
inline bool admit_picto_edit(uint64_t base,uint64_t object,uint64_t function,uint64_t owner,const CallPacket& p) {
if(p.entry_rva!=0x13937a0 || p.object_count || p.return_offset!=65535 || (p.version!=1 && p.version!=2) || (local_read<uint32_t>(object+8)&0x30)) return false;
auto cls=local_read<uint64_t>(object+0x10);
if(exact_name(base,function+0x18,"RefreshSlotData") && exact_name(base,owner+0x18,"WBP_Panel_Pictos_C") &&
exact_name(base,local_read<uint64_t>(owner+0x20)+0x18,"/Game/UI/Widgets/InGame_Menu/Pictos_Panel/WBP_Panel_Pictos") &&
exact_name(base,cls+0x18,"WBP_Panel_Pictos_C") && exact_name(base,local_read<uint64_t>(cls+0x20)+0x18,"/Game/UI/Widgets/InGame_Menu/Pictos_Panel/WBP_Panel_Pictos")) {
if(!picto_stable_script(base,function,0))return false;
if(p.field_count!=1 || p.fields[0].kind!=CallInt32 || p.fields[0].offset) return false;
const auto slot=local_read<int32_t>(reinterpret_cast<uint64_t>(p.data)); return slot>=0 && slot<=2;
}
if(exact_name(base,function+0x18,"UpdateEquipmentStats") && exact_name(base,owner+0x18,"BP_CharacterData_C") &&
exact_name(base,local_read<uint64_t>(owner+0x20)+0x18,"/Game/Gameplay/CharacterData/BP_CharacterData") &&
exact_name(base,cls+0x18,"BP_CharacterData_C") && exact_name(base,local_read<uint64_t>(cls+0x20)+0x18,"/Game/Gameplay/CharacterData/BP_CharacterData")) {
if(!picto_stable_script(base,function,6))return false;
return p.field_count==0;
}
if(exact_name(base,function+0x18,"RefreshCurrentGearStats") && exact_name(base,owner+0x18,"BP_ItemInstance_Gear_C") &&
exact_name(base,local_read<uint64_t>(owner+0x20)+0x18,"/Game/Gameplay/Pictos/BP_ItemInstance_Gear") &&
exact_name(base,cls+0x18,"BP_ItemInstance_Gear_Pictos_C") && exact_name(base,local_read<uint64_t>(cls+0x20)+0x18,"/Game/Gameplay/Pictos/BP_ItemInstance_Gear_Pictos")) {
if(!picto_stable_script(base,function,2))return false;
return p.field_count==0;
}
if(exact_name(base,function+0x18,"SetBaseStatsMultiplier") && exact_name(base,owner+0x18,"BP_ItemInstance_Gear_C") &&
exact_name(base,local_read<uint64_t>(owner+0x20)+0x18,"/Game/Gameplay/Pictos/BP_ItemInstance_Gear") &&
exact_name(base,cls+0x18,"BP_ItemInstance_Gear_Pictos_C") && exact_name(base,local_read<uint64_t>(cls+0x20)+0x18,"/Game/Gameplay/Pictos/BP_ItemInstance_Gear_Pictos")) {
if(!picto_stable_script(base,function,3))return false;
if(p.field_count!=2 || p.fields[0].kind!=CallByte || p.fields[0].offset || p.fields[1].kind!=CallDouble || p.fields[1].offset!=8) return false;
const auto key=p.data[0]; const auto value=local_read<double>(reinterpret_cast<uint64_t>(p.data)+8);
return (key==1 || key==6 || key==8 || key==9) && std::isfinite(value) && value>=0. && value<=10.;
}
return false;
}