    bool helper_battle_quiescent(uint64_t b){
        if(!source_current(b,true))return false; // no exploration-pawn dependency during combat
        const auto observed=skin_reference(b,ids_[0],"BP_jRPG_Controller_World_C",
            "/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_Controller_World","AC_jRPG_BattleManager",
            2336,0x8001400080204ULL,"AC_jRPG_BattleManager_C");
        const auto manager=observed.address;
        if(!manager||(local_read<uint32_t>(manager+8)&0x40018030U)||
           local_read<uint64_t>(manager+32)!=ids_[0].address||
           !arena_class(b,manager,"AC_jRPG_BattleManager_C","/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_BattleManager"))return false;
        e33_battle_state::Observation observation{};
        if(!e33_battle_state::observe(b,manager,observation))return false;
        const bool idle=observation.idle();
        bool own_active=false;
        if(helper_entry_.pending()){
            const auto owned_arena=arena_staging_?actor_:arena_binding_.observed_arena();
            own_active=observation.started&&observation.enemy_count>0&&observation.encounter_name==helper_entry_.name()&&
                call_identity(b,owned_arena)&&observation.arena==owned_arena.address;
        }
        helper_entry_.observe(own_active,idle);
        return idle&&helper_entry_.ready();
    }
