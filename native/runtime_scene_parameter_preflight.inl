// Included in Owner's public section. A native visual may supply independent
// ownership/context/arena proofs to the existing parameter transaction. This
// version deliberately supplies NO dispatch callback: ground/assembly admission
// and battle retirement must be established before combat can be authorized.
    bool visual_parameter_instance(uint64_t base,uint64_t token,const CallIdentity& actor,uint64_t& name){
        name=0;
        if(base!=base_ || !token || token!=owner_ || !visual_staging_ || !pool_ || state_!=9 ||
           plan_.count!=1. || !same(actor,characters_[0]) || !valid(actor) || !current() ||
           !primary_lease_ || !leases_.owns_object(owner_,primary_lease_,actor.address) ||
           !named(base_,local_read<uint64_t>(actor.address+16),"SkeletalMeshActor","/Script/Engine") ||
           !valid(components_[0]) || exact_name(base_,actor.address+24,"None"))return false;
        name=local_read<uint64_t>(actor.address+24);return name!=0;
    }
    bool visual_parameter_arena(uint64_t base,uint64_t token,const CallIdentity& actor,CallIdentity& arena){
        arena={};uint64_t name=0;
        if(!visual_parameter_instance(base,token,actor,name) || !visual_arena_state_.verified ||
           !valid(visual_world_) || !visual_arena_binding_.preflight() ||
           !visual_arena_binding_.dependencies_supported())return false;
        for(unsigned i=0;i<5;++i)
            if(!valid(visual_arena_ids_[i]) || !visual_arena_leases_[i] ||
               !leases_.owns_object(owner_,visual_arena_leases_[i],visual_arena_ids_[i].address))return false;
        arena=visual_arena_ids_[1];return true;
    }
    bool visual_parameter_copy_arena(uint64_t base,uint64_t token,const CallIdentity& actor,
            const CallIdentity& expected,void* destination){
        CallIdentity arena{};
        if(!destination || !visual_parameter_arena(base,token,actor,arena) || !same(expected,arena))return false;
        visual_arena_state_.temporary_live=true;
        if(!visual_arena_binding_.copy_soft_reference(destination) ||
           !visual_arena_binding_.verify_soft_reference(destination))return false;
        return e33_enemy_spawn::close_arena_binding_temporary(visual_arena_binding_,visual_arena_state_);
    }
    bool visual_parameter_context(uint64_t base,uint64_t token,const CallIdentity& actor,
            const CallIdentity& manager,const CallIdentity& function,uint64_t& name){
        CallIdentity arena{};name=0;
        if(!visual_parameter_instance(base,token,actor,name) ||
           !visual_parameter_arena(base,token,actor,arena) || !valid(manager) || !valid(function))return false;
        e33_npc_presentation::CurrentContextGuard context{base_,ids_[1],visual_world_};
        e33_battle_state::Observation observed{};CallIdentity current_manager{};
        return context.observe_battle(observed,&current_manager) && observed.idle() && same(manager,current_manager) &&
            local_read<uint64_t>(function.address+32)==local_read<uint64_t>(manager.address+16) &&
            exact_name(base_,function.address+24,"StartBattleNEW");
    }
    uint32_t bind_visual_parameter_arena(const CallIdentity (&query)[5]){
        uint64_t name=0;
        if(visual_arena_requested_ || !visual_parameter_instance(base_,owner_,characters_[0],name))return 2047;
        for(const auto& id:query)if(!valid(id))return 2047;
        e33_npc_presentation::CurrentContextGuard context{base_,ids_[1],query[0]};
        if(!context.battle_quiescent() || !e33_enemy_spawn::arena_world(base_,characters_[0].address,query[0].address) ||
           leases_.preflight(owner_,5)!=StrongLeaseResult::Ok)return 2047;
        visual_arena_requested_=true;visual_world_=query[0];
        std::memcpy(visual_arena_ids_,query,sizeof(visual_arena_ids_));
        auto configure=[&](){
            visual_arena_binding_.configure_owned_presentation_value(base_,visual_world_.address,characters_[0],
                visual_arena_ids_[1],visual_arena_ids_[2],visual_arena_ids_[3],visual_arena_ids_[4],this,
                [](void* opaque,uint64_t b,const CallIdentity& actor,uint64_t world){
                    auto& held=*static_cast<Owner*>(opaque);uint64_t instance=0;
                    return world==held.visual_world_.address && held.visual_parameter_instance(b,held.owner_,actor,instance);
                });
        };
        configure();if(!visual_arena_binding_.preflight())return 2047;
        for(unsigned i=0;i<5;++i){
            TargetStrongReferenceOps refs{base_,visual_arena_ids_[i]};
            if(leases_.acquire(refs,owner_,visual_arena_ids_[i].address,visual_arena_leases_[i])!=StrongLeaseResult::Ok ||
               !stabilize_retained_identity(refs,visual_arena_ids_[i]))return 2048;
        }
        visual_world_=visual_arena_ids_[0];configure();
        return e33_enemy_spawn::bind_owned_arena(visual_arena_binding_,visual_arena_state_)==
            e33_enemy_spawn::ArenaBindingResult::Ok?0:2048;
    }
