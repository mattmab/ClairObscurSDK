#pragma once
#include <cstdint>
// Pre-dispatch retirement gate. 407 is the SDK's existing cleanup deferral;
// schema uncertainty must never be interpreted as an out-of-battle actor.
template<class Ops>
uint32_t enemy_retirement_gate(Ops& ops,bool has_work,bool world_actor){
    if(!has_work)return 0;
    if(!ops.context())return 407;
    if(world_actor){
        bool in_battle=false;
        if(!ops.battle_state(in_battle))return 2937;
        if(in_battle)return 407;
    }
    return 0;
}
