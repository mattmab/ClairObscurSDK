#pragma once
#include "game_owned_cinematic_admission.h"
#include "catalog_game_owned_actions.h"

// Included after call_identity/capture/is_class. A two-function exception to
// the Blueprint ban; all normal reflected invocation checks still execute.
struct TargetGameOwnedCinematic {
    uint64_t base,object,function,owner;
    bool valid(uint64_t value)const {auto id=call_capture(base,value);return id.address && call_identity(base,id)==value;}
    bool named(uint64_t value,const char* name,const char* package)const {
        if(!valid(value) || !exact_name(base,value+24,name))return false;
        const auto outer=local_read<uint64_t>(value+32);
        return valid(outer) && exact_name(base,outer+24,package);
    }
    bool live_target()const {
        return valid(object) && valid(function) && valid(owner) && call_is_class(base,owner) &&
            !(local_read<uint32_t>(object+8)&0x40000030) && local_read<uint64_t>(object+16)==owner &&
            local_read<uint64_t>(function+32)==owner &&
            named(local_read<uint64_t>(function+16),"Function","/Script/CoreUObject");
    }
    bool exact_function(GameOwnedCinematicCall kind)const {
        return kind==GameOwnedCinematicCall::teleport_safe ?
            named(owner,"WBP_PauseMenu_C","/Game/UI/Widgets/InGame_Menu/PauseMenu/WBP_PauseMenu") &&
                exact_name(base,function+24,"TeleportToSafeLocation") :
            kind==GameOwnedCinematicCall::execute_scavenger &&
            named(owner,"BP_GameActionExecutorComponent_C","/Game/Gameplay/GameActionsSystem/BP_GameActionExecutorComponent") &&
                exact_name(base,function+24,"ExecuteGameAction");
    }
    bool field(uint64_t value,const char* name,uint32_t offset,uint64_t table,uint64_t flags)const {
        return value && local_read<uint64_t>(value)==base+table && local_read<uint64_t>(value+0x10)==(function|1) &&
            exact_name(base,value+0x20,name) && local_read<uint32_t>(value+0x30)==1 &&
            local_read<uint32_t>(value+0x34)==8 && local_read<uint64_t>(value+0x38)==flags &&
            local_read<uint32_t>(value+0x44)==offset;
    }
    bool exact_schema(GameOwnedCinematicCall kind)const {
        auto first=local_read<uint64_t>(function+0x50);if(!first)return false;
        auto second=local_read<uint64_t>(first+0x18);if(!second || local_read<uint64_t>(second+0x18))return false;
        if(kind==GameOwnedCinematicCall::teleport_safe) {
            return field(first,"CallFunc_ComputeSafeLocation_LevelAssetName",0,0x6e13040,0x8001040000200ULL) &&
                field(second,"CallFunc_ComputeSafeLocation_SpawnPointTag",8,0x6e136a0,0x8001000000000ULL) &&
                named(local_read<uint64_t>(second+0x70),"GameplayTag","/Script/GameplayTags");
        }
        return kind==GameOwnedCinematicCall::execute_scavenger &&
            field(first,"GameAction",0,0x6e11d38,0x8001000000294ULL) &&
            named(local_read<uint64_t>(first+0x70),"GameAction","/Script/SandFall") &&
            field(second,"CallFunc_ConstructAndBindGameActionInstance_GameActionInstance",8,0x6e11d38,0x8001000000200ULL) &&
            named(local_read<uint64_t>(second+0x70),"GameActionInstance","/Script/SandFall");
    }
    bool game_action_constraint(const CallIdentity& id)const {
        return id.address && call_identity(base,id)==id.address && call_is_class(base,id.address) && named(id.address,"GameAction","/Script/SandFall");
    }
    // Legacy internal name; optional catalog expansion retains the exact class guard.
    bool original_scavenger(const CallIdentity& id)const {
        if(!id.address || call_identity(base,id)!=id.address || (local_read<uint32_t>(id.address+8)&0x40000030))return false;
        const auto cls=local_read<uint64_t>(id.address+16);
        return call_is_class(base,cls) &&
            named(cls,"BP_GameAction_CinematicWithLightingScenario_C","/Game/Gameplay/GameActionsSystem/Cinematic/BP_GameAction_CinematicWithLightingScenario") &&
            (named(id.address,"DA_GA_CIN_MCS_ScavengerIntro","/Game/Levels/OrangeForest/GameActions/DA_GA_CIN_MCS_ScavengerIntro") ||
             catalog_game_owned_action([&](const char* name,const char* package) {
                 return named(id.address,name,package);
             }));
    }
};
