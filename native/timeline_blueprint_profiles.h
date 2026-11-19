#pragma once
// Exact classes observed in authored cinematic templates. Construction uses
// the existing owned deferred-spawn journal; no mesh/face reconstruction.
namespace e33_timeline_blueprint {
struct Profile {const char* name;const char* package;};
inline constexpr Profile profiles[]={
    {"BP_Cine_Lune_C","/Game/Characters/Heros/Cinematics/BP_Cine_Lune"},
    {"BP_Cine_Sciel_C","/Game/Characters/Heros/Cinematics/BP_Cine_Sciel"},
    {"BP_Cine_Verso_C","/Game/Characters/Heros/Cinematics/BP_Cine_Verso"}
#if E33_RUNTIME_CINEMATIC_VERSION >= 236
    ,
    {"BP_Cine_Maelle_C","/Game/Characters/Heros/Cinematics/BP_Cine_Maelle"},
    {"BP_Cine_Monoco_C","/Game/Characters/Heros/Cinematics/BP_Cine_Monoco"}
#endif
#if E33_RUNTIME_CINEMATIC_VERSION>=266
    ,{"BP_Cine_FacelessBoy_C","/Game/Characters/NPCs/Cinematics/BP_Cine_FacelessBoy"}
#endif
#if E33_RUNTIME_CINEMATIC_VERSION>=268
    ,{"BP_NPC_Dialogue_Empty_FacelessBoyFinale_C","/Game/Characters/NPCs/Lumiere/DialogueNPCs/WalkToHarbour/BP_NPC_Dialogue_Empty_FacelessBoyFinale"}
#endif
#if E33_RUNTIME_CINEMATIC_VERSION>=284
    ,{"BP_Cine_Noah_C","/Game/Characters/Heros/Cinematics/BP_Cine_Noah"}
    ,{"BP_JRPG_NPC_Dialog_NPC_Sophie_NoInteraction_C","/Game/Characters/Heros/Sophie/BP_JRPG_NPC_Dialog_NPC_Sophie_NoInteraction"}
    ,{"BP_jRPG_NPC_Dialog_SpiritClea_C","/Game/Characters/NPCs/Spirits/SpiritClea/BP_jRPG_NPC_Dialog_SpiritClea"}
    ,{"BP_jRPG_NPC_Dialog_RenoirSpirit_C","/Game/Characters/NPCs/Spirits/SpiritRenoir/BP_jRPG_NPC_Dialog_RenoirSpirit"}
#endif
#if E33_RUNTIME_CINEMATIC_VERSION>=249
    ,{"CameraActor","/Script/Engine"}
#endif
#if E33_RUNTIME_CINEMATIC_VERSION>=287
    ,{"BP_InvisibleWall_NavModifier_C","/Game/LevelTools/InvisibleWalls/BP_InvisibleWall_NavModifier"}
    ,{"BP_jRPG_MapTeleportPoint_Interactible_C","/Game/LevelTools/BP_jRPG_MapTeleportPoint_Interactible"}
#if E33_RUNTIME_CINEMATIC_VERSION>=296
    ,{"BP_WP_StreamingSourceComponent_C","/Game/Gameplay/GameplayElement/Content/StreamingSource/BP_WP_StreamingSourceComponent"}
#endif
#endif
};
}
