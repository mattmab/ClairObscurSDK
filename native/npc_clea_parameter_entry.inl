// Included in CleaOwner's public section. Uses the same retained arena value and
// shared frame transactions as world enemies; these callbacks cannot dispatch.
    template<class Pool> bool owned_entry_arena(uint64_t base,uint64_t session,Pool& pool,
            const CallIdentity& actor,CallIdentity& arena){
        uint64_t name=0;arena={};
        if(!owned_parameter_instance_name(base,session,pool,actor,name)||!arena_binding_state_.verified||
           arena_dependency_pending_||arena_value_closed_)return false;
        for(unsigned i=0;i<4;++i)if(!arena_leases_[i]||!call_identity(base,arena_ids_[i])||
            !pool.owns_object(session,arena_leases_[i],arena_ids_[i].address))return false;
        if(!arena_binding_.preflight()||!arena_binding_.dependencies_supported())return false;
        arena=arena_ids_[0];return true;
    }
    template<class Pool> bool copy_entry_arena(uint64_t base,uint64_t session,Pool& pool,
            const CallIdentity& actor,const CallIdentity& expected,void* destination){
        CallIdentity arena{};
        if(!destination||!owned_entry_arena(base,session,pool,actor,arena)||
           arena.index!=expected.index||arena.serial!=expected.serial||arena.address!=expected.address)return false;
        arena_binding_state_.temporary_live=true;
        if(!arena_binding_.copy_soft_reference(destination)||!arena_binding_.verify_soft_reference(destination))return false;
        return e33_enemy_spawn::close_arena_binding_temporary(arena_binding_,arena_binding_state_);
    }
    template<class Pool> bool owned_entry_context(uint64_t base,uint64_t session,Pool& pool,
            const CallIdentity& actor,const CallIdentity& manager,const CallIdentity& function,uint64_t& name){
        name=0;CallIdentity arena{};
        if(!owned_parameter_instance_name(base,session,pool,actor,name)||!owned_entry_arena(base,session,pool,actor,arena)||
           !call_identity(base,manager)||!call_identity(base,function))return false;
        CurrentContextGuard context{base,source_.controller,source_.world};
        e33_battle_state::Observation state{};CallIdentity current_manager{};
        if(!context.observe_battle(state,&current_manager)||!state.idle()||
           manager.index!=current_manager.index||manager.serial!=current_manager.serial||manager.address!=current_manager.address)return false;
        return local_read<uint64_t>(function.address+32)==local_read<uint64_t>(manager.address+16)&&
            exact_name(base,function.address+24,"StartBattleNEW");
    }
