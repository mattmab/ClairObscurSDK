#pragma once
namespace e33_enemy_spawn {
// A staged visual helper belongs to its retained world/controller, not the
// exploration pawn used to place it. Mounted possession may change that pawn.
// Ordinary enemy entry keeps its existing pawn-specific validation.
template<class Ops> bool helper_entry_source_context(Ops& ops,bool visual){
    return visual?ops.source_current():ops.pawn_current();
}
// A constructed original visual helper has no world-enemy initializer or
// IsInBattle field. Its parameter-copy authority comes from its owned lifetime
// and a fresh idle battle context. This proof grants no placement or dispatch.
struct HelperParameterAnchorProof {
    bool owned_identity=false,current_context=false,original_helper=false;
    bool arena=false,prepared=false,construction_complete=false,battle_quiescent=false;
};
inline bool helper_parameter_anchor_admitted(const HelperParameterAnchorProof& p){
    return p.owned_identity&&p.current_context&&p.original_helper&&!p.arena&&
        p.prepared&&p.construction_complete&&p.battle_quiescent;
}
}
