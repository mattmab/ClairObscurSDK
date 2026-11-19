#pragma once
#include <cstdint>

// Timeline-only owners cannot dispatch encounter initialization. Their reviewed
// cast/camera/interaction actors need no combat-manager observation to retire.
// Preserve the gate whenever an actual helper entry journal exists.
inline bool helper_requires_battle_quiescence(bool visual,bool timeline_only,bool has_entry){
    return has_entry||(visual&&!timeline_only);
}

// Helper actors have no world-enemy IsInBattle flag. A fresh controller-owned
// manager must prove quiescence before their visual/arena resources can retire.
template<class Ops>
uint32_t helper_retirement_gate(Ops& ops,bool has_work,bool helper){
    if(!has_work||!helper)return 0;
    bool quiescent=false;
    if(!ops.context()||!ops.fresh_battle_quiescent(quiescent)||!quiescent)return 407;
    return 0;
}
