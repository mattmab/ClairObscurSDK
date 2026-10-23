#pragma once
#include <cstdint>

// Helper actors have no world-enemy IsInBattle flag. A fresh controller-owned
// manager must prove quiescence before their visual/arena resources can retire.
template<class Ops>
uint32_t helper_retirement_gate(Ops& ops,bool has_work,bool helper){
    if(!has_work||!helper)return 0;
    bool quiescent=false;
    if(!ops.context()||!ops.fresh_battle_quiescent(quiescent)||!quiescent)return 407;
    return 0;
}
