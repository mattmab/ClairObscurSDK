#pragma once
#include "target_battle_parameter_frame.h"
#include "battle_parameter_arena.h"

namespace e33_enemy_spawn {
// Bind a staged, assembly-checked current-map arena to an owned clone. Default
// admission preserves authored arena references; replacing them requires an
// explicit current-arena policy. Nonempty data-layer dependencies stay rejected.
template<class Pool,class EnemyOwner> struct TargetBattleParameterArenaOps {
    TargetBattleParameterOps<Pool> frame;
    EnemyOwner& enemy;uint64_t actor_owner;CallIdentity actor;bool explicit_current_arena=false;
    uint32_t rejection=3063;
    ParameterCall bind(void* parameters){
        rejection=3066;
        if(!parameters||!frame.preflight()||!frame.destination_separate(parameters))return ParameterCall::NotDispatched;
        const auto structure=frame.structure.address;
        const auto hard=frame.field(structure,"BattleMapBP_18_E90DB870407FE894CA7200B075D98B4A",32,8,0x6e11d38,0x8001000000a05ULL);
        const auto soft=frame.field(structure,"BattleMapBPSoft_41_9D55F2484E1768C57CF31794DEDE717F",40,40,0x6e128d8,0x8000000000005ULL);
        const auto layers=frame.field(structure,"BattleMapDataLayers_55_4664B50E490D09A9318C6E8B7DAE07BB",80,16,0x6e0de80,5);
        rejection=3067;if(!hard||!soft||!layers)return ParameterCall::NotDispatched;
        rejection=3068;if(!frame.named(local_read<uint64_t>(hard+0x70),"BP_BattleMap_C","/Game/Levels/Battle_Maps/BP_BattleMap"))return ParameterCall::NotDispatched;
        auto* bytes=static_cast<uint8_t*>(parameters);
        const auto at=reinterpret_cast<uint64_t>(parameters);
        // Conservative exact empty representation; do not decode an arbitrary
        // soft path or replace an unloaded but authored arena with a default.
        rejection=3069;if(!explicit_current_arena&&local_read<uint64_t>(at+32))return ParameterCall::NotDispatched;
        rejection=3070;if(!explicit_current_arena&&!empty_battle_arena_soft_value(bytes+40))return ParameterCall::NotDispatched;
        rejection=3071;if(local_read<int32_t>(at+88)!=0||local_read<int32_t>(at+92)<0||local_read<int32_t>(at+92)>4096)return ParameterCall::NotDispatched;
        CallIdentity arena{};
        rejection=3072;
        if(!enemy.owned_entry_arena(frame.base,frame.session,frame.leases,actor_owner,actor,arena))return ParameterCall::NotDispatched;
        std::array<uint8_t,344> before{};std::memcpy(before.data(),bytes,before.size());
        if(!enemy.copy_entry_arena(frame.base,frame.session,frame.leases,actor_owner,actor,arena,bytes+40))return ParameterCall::Unknown;
        std::memcpy(bytes+32,&arena.address,8);
        for(size_t i=0;i<before.size();++i)
            if((i<32||i>=80)&&before[i]!=bytes[i])return ParameterCall::Unknown;
        rejection=0;
        return frame.preflight()&&frame.valid(arena)&&local_read<uint64_t>(at+32)==arena.address?
            ParameterCall::Completed:ParameterCall::Unknown;
    }
};
}
