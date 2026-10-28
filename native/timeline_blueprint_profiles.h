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
};
}
