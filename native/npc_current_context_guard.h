#pragma once
#include "owned_component_visit.h"
#include "battle_quiescence_observation.h"
namespace e33_npc_presentation {
// Fresh per-call manager discovery: the original game recreates this component
// after battles. A cached old idle manager cannot authorize another spawn.
struct CurrentContextGuard {
    uint64_t base;CallIdentity controller,world;
    bool current_context(){
        if(!TargetPodSchemaOps{base}.context()||!call_identity(base,controller)||!call_identity(base,world)||
           (local_read<uint32_t>(controller.address+8)&0x40018030U)||
           (local_read<uint32_t>(world.address+8)&0x40018030U)||
           !e33_mesh::named(base,local_read<uint64_t>(world.address+16),"World","/Script/Engine"))return false;
        auto outer=controller.address;unsigned walked=0;
        for(;outer&&outer!=world.address&&++walked<32;outer=local_read<uint64_t>(outer+32)){}
        return outer==world.address;
    }
    bool observe_battle(e33_battle_state::Observation& observation,CallIdentity* identity=nullptr){
        observation={};
        if(!current_context())return false;
        uint64_t manager=0;
        if(!e33_owned_actor::visit_components(base,controller.address,[&](uint64_t component){
            if(!e33_mesh::named(base,local_read<uint64_t>(component+16),"AC_jRPG_BattleManager_C",
               "/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_BattleManager"))return true;
            if(manager&&manager!=component)return false;
            manager=component;return true;
        })||!manager)return false;
        if(!e33_battle_state::observe(base,manager,observation)||!current_context())return false;
        if(identity){*identity=call_capture(base,manager);if(!identity->address)return false;}
        return true;
    }
    bool battle_quiescent(){
        e33_battle_state::Observation observation{};
        return observe_battle(observation)&&observation.idle();
    }
};
}
