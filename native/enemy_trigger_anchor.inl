    // Original trigger anchors are hidden research carriers, never ordinary
    // enemies or visual recipes. All other enemy operations remain unavailable.
    template<class Pool> struct TriggerLeaseOps {
        uint64_t base,session;Pool& pool;
        CallIdentity capture(uint64_t object){return call_capture(base,object);}
        bool exact_retained(CallIdentity id,uint64_t token){
            return call_identity(base,id)&&pool.owns_object(session,token,id.address);
        }
        bool retain(CallIdentity& id,uint64_t& token){
            TargetStrongReferenceOps ops{base,id};
            return pool.acquire(ops,session,id.address,token)==StrongLeaseResult::Ok&&stabilize_retained_identity(ops,id);
        }
        bool release(uint64_t token){
            TargetStrongReferenceOps ops{base,{-1,0,0}};
            return pool.release(ops,session,token)==StrongLeaseResult::Ok;
        }
    };
    uint64_t trigger_game_instance(uint64_t b){
        uint64_t descriptor=0;
        const auto at=picto_field(b,ids_[2].address,"OwningGameInstance","ObjectProperty",472,8,&descriptor);
        if(!at||!descriptor||local_read<uint64_t>(descriptor)!=b+0x6e11d38||
           local_read<uint64_t>(descriptor+0x38)!=0x14c001000002200ULL)return 0;
        const auto gi=local_read<uint64_t>(at);
        return call_identity(b,call_capture(b,gi))&&!(local_read<uint32_t>(gi+8)&0x40018030U)&&named(b,local_read<uint64_t>(gi+16),
            "BP_jRPG_GI_Custom_C","/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_GI_Custom")?gi:0;
    }
    bool trigger_context(uint64_t b){
        return source_current(b,true)&&trigger_targets_.count&&
            call_identity(b,trigger_targets_.identities[0])&&
            trigger_game_instance(b)==trigger_targets_.identities[0].address;
    }
    template<class Pool> bool trigger_begin(uint64_t b,uint64_t session,Pool& pool){
        if(pool.preflight(session,8)!=StrongLeaseResult::Ok)return false;
        const auto gi=trigger_game_instance(b);if(!gi)return false;
        TriggerLeaseOps<Pool> ops{b,session,pool};
        return trigger_targets_.add(ops,gi)&&helper_battle_quiescent(b);
    }
    bool trigger_held(uint64_t b){
        uint64_t hd=0,cd=0;
        const auto h=picto_field(b,actor_.address,"bHidden","BoolProperty",88,1,&hd);
        const auto c=picto_field(b,actor_.address,"bActorEnableCollision","BoolProperty",92,1,&cd);
        return h&&c&&hd&&cd&&local_read<uint32_t>(hd+0x70)==0x80800001U&&
            local_read<uint32_t>(cd+0x70)==0x80800001U&&(local_read<uint8_t>(h)&0x80)&&!(local_read<uint8_t>(c)&0x80);
    }
    template<class Pool> bool trigger_capture_components(uint64_t b,uint64_t session,Pool& pool){
        if(trigger_components_complete_)return true;
        if(trigger_capture_attempted_||trigger_targets_.acquire_pending)return false;
        trigger_capture_attempted_=true;
        TriggerLeaseOps<Pool> ops{b,session,pool};
        const auto capture=[&](uint64_t object){
            const auto cls=local_read<uint64_t>(object+16);
            const bool condition=named(b,cls,"BP_ConditionCheckerComponent_C","/Game/Gameplay/ConditionChecker/BP_ConditionCheckerComponent");
            const bool serializable=named(b,cls,"BP_Interaction_SerializableComponent_C",e33_trigger_anchor::interaction_package);
            if(!condition&&!serializable&&!named(b,cls,"SceneComponent","/Script/Engine")&&
               !named(b,cls,"BoxComponent","/Script/Engine")&&!named(b,cls,"StaticMeshComponent","/Script/Engine"))return false;
            if(!trigger_targets_.add(ops,object))return false;
            const auto id=trigger_targets_.identities[trigger_targets_.count-1];
            if(condition){
                if(trigger_condition_.address||!e33_npc_presentation::empty_condition_wrapper(b,id))return false;
                trigger_condition_=id;
            }
            if(serializable){
                if(trigger_serializable_.address||!e33_trigger_anchor::serializable_field(b,object,actor_.address))return false;
                trigger_serializable_=id;
            }
            return true;
        };
        if(!e33_owned_actor::visit_components(b,actor_.address,capture))return false;
        trigger_components_complete_=true;return true;
    }
    template<class Pool> bool trigger_finalize(uint64_t b,uint64_t session,Pool& pool){
        if(!trigger_context(b)||!pool.owns_object(session,lease_,actor_.address)||
           !trigger_capture_components(b,session,pool)||trigger_targets_.count!=6||
           !trigger_condition_.address||!trigger_serializable_.address||trigger_refresh_attempted_)return false;
        const auto field=e33_trigger_anchor::serializable_field(b,trigger_serializable_.address,actor_.address);
        if(!field||!exact_name(b,field,"None")||exact_name(b,actor_.address+24,"None"))return false;
        const auto name=local_read<uint64_t>(actor_.address+24);
        // Only the private component is assigned. ResetCategory stays zero;
        // neither a CDO nor either campaign history map is modified.
        std::memcpy(reinterpret_cast<void*>(field),&name,8);
        if(local_read<uint64_t>(field)!=name||
           !e33_trigger_anchor::refresh_preflight(b,trigger_refresh_,actor_))return false;
        trigger_refresh_attempted_=true;
        if(!e33_trigger_anchor::invoke_refresh(b,trigger_refresh_,actor_))return false;
        trigger_refresh_acknowledged_=true;
        if(!hide_prepared(b)||!trigger_held(b)||!trigger_context(b)||
           local_read<uint64_t>(field)!=name||!e33_trigger_anchor::refresh_preflight(b,trigger_refresh_,actor_))return false;
        trigger_ready_=true;return true;
    }
    // Source-copy proof only. No placement, reveal, entry or quest authority.
    template<class Pool> bool trigger_parameter_name(uint64_t b,uint64_t session,Pool& pool,
            uint64_t token,const CallIdentity& observed,uint64_t& name,bool binding_preflight=false){
        name=0;
        if(!trigger_anchor_||arena_staging_||!owner_||token!=owner_||!lease_||!preparing_world_||
           !trigger_ready_||!trigger_capture_attempted_||!trigger_components_complete_||
           !trigger_refresh_attempted_||!trigger_refresh_acknowledged_||
           trigger_actor_retention_pending_||trigger_targets_.count!=6||trigger_targets_.acquire_pending||
           trigger_targets_.release_pending||trigger_targets_.released||trigger_arena_cleanup_pending_||
           trigger_retirement_!=e33_owned_actor::RetirementPhase::Ready||
           construction_.phase!=e33_owned_actor::ConstructionPhase::Complete||
           // EngineArenaBinding must revalidate this held actor while the
           // already journalled soft-reference copy is in progress. External
           // source/entry proofs still reject an outstanding temporary.
           (arena_binding_state_.attempted&&(!arena_binding_state_.verified||
               (arena_binding_state_.temporary_live&&!binding_preflight)))||
           observed.index!=actor_.index||observed.serial!=actor_.serial||observed.address!=actor_.address||
           !call_identity(b,actor_)||!pool.owns_object(session,lease_,actor_.address)||
           (local_read<uint8_t>(actor_.address+0x5d)&1)||
           local_read<uint64_t>(actor_.address+16)!=ids_[4].address||
           !arena_world(b,actor_.address,ids_[2].address))return false;
        bool serializable=false,condition=false;
        for(size_t i=0;i<trigger_targets_.count;++i){
            const auto held_target=trigger_targets_.identities[i];
            if(!call_identity(b,held_target)||!trigger_targets_.leases[i]||
               !pool.owns_object(session,trigger_targets_.leases[i],held_target.address)||
               (i&&local_read<uint64_t>(held_target.address+32)!=actor_.address))return false;
            if(held_target.index==trigger_serializable_.index&&held_target.serial==trigger_serializable_.serial&&held_target.address==trigger_serializable_.address)serializable=true;
            if(held_target.index==trigger_condition_.index&&held_target.serial==trigger_condition_.serial&&held_target.address==trigger_condition_.address)condition=true;
        }
        if(!trigger_context(b)||!trigger_held(b)||!helper_battle_quiescent(b)||
           !e33_trigger_anchor::safe_empty_instance(b,actor_.address))return false;
        const auto condition_slot=e33_trigger_anchor::component_slot(b,actor_.address,"BP_ConditionCheckerComponent",672,
            "BP_ConditionCheckerComponent_C",e33_trigger_anchor::condition_package);
        if(!serializable||!condition||!condition_slot||local_read<uint64_t>(condition_slot)!=trigger_condition_.address)return false;
        const auto field=e33_trigger_anchor::serializable_field(b,trigger_serializable_.address,actor_.address);
        const auto owned_name=local_read<uint64_t>(actor_.address+24);
        if(!field||!owned_name||exact_name(b,actor_.address+24,"None")||local_read<uint64_t>(field)!=owned_name)return false;
        name=owned_name;return true;
    }
    template<class Pool> bool retired_trigger_proven(uint64_t b,uint64_t session,Pool& pool){
        using namespace e33_owned_actor;
        const bool purged=purged_owned_actor(b,session,pool);
        if(!trigger_ready_||!trigger_components_complete_||trigger_targets_.count!=6||
           trigger_targets_.acquire_pending||trigger_targets_.release_pending||trigger_actor_retention_pending_||
           trigger_retirement_==RetirementPhase::UnregisterPending||trigger_retirement_==RetirementPhase::DestroyPending||
           trigger_retirement_==RetirementPhase::ReleasePending||
           (!purged&&!externally_retired_owned_actor(b,session,pool)))return false;
        CallIdentity targets[8]{};size_t count=0;targets[count++]=actor_;
        for(size_t i=0;i<trigger_targets_.count;++i){
            const auto id=trigger_targets_.identities[i];
            if(purged&&i){
                if(call_identity(b,id)||!pool.owns_retirement_storage(session,trigger_targets_.leases[i],id.address))return false;
                targets[count++]=id;
            }else{
                if(!call_identity(b,id)||!pool.owns_object(session,trigger_targets_.leases[i],id.address))return false;
                if(i){if(local_read<uint64_t>(id.address+32)!=actor_.address)return false;targets[count++]=id;}
            }
        }
        uint32_t total=0,owned=0;
        return e33_npc_presentation::observe_listener_field(b,trigger_targets_.identities[0],
            e33_npc_presentation::listener_fields[0],targets,count,total,owned)&&owned==0;
    }
    uint32_t close_trigger_arena(uint64_t b,bool retired=false){
        if(trigger_arena_cleanup_pending_)return 3653;
        if(!arena_binding_state_.attempted)return 0;
        if(!retired&&(!trigger_context(b)||!helper_battle_quiescent(b)))return 407;
        // Both engine cleanup calls may mutate before failure/SEH. Persist the
        // pending flag first; never destroy the anchor or replay uncertain work.
        trigger_arena_cleanup_pending_=true;
        if(!close_arena_binding_temporary(arena_binding_,arena_binding_state_)||!arena_binding_.close_owned_value())return 3653;
        trigger_arena_cleanup_pending_=false;
        arena_binding_state_={};arena_binding_={};trigger_arena_pool_=nullptr;trigger_arena_session_=0;
        return 0;
    }
    template<class Pool> uint32_t close_trigger(uint64_t b,uint64_t session,Pool& pool){
        using namespace e33_owned_actor;
        if(!TargetStrongReferenceOps{b,{-1,0,0}}.can_release())return 407;
        if(allocation_unresolved(construction_,actor_.address!=0))return 3643;
        if(trigger_targets_.acquire_pending||trigger_targets_.release_pending||trigger_actor_retention_pending_||
           (trigger_capture_attempted_&&!trigger_components_complete_))return 3653;
        const bool retired=retired_trigger_proven(b,session,pool);
        const auto arena_cleanup=close_trigger_arena(b,retired);if(arena_cleanup)return arena_cleanup;
        TriggerLeaseOps<Pool> leases{b,session,pool};
        if(retired){
            // Engine world teardown already ran destruction/EndPlay. Only
            // release this owner's verified holds; never dispatch destruction
            // or substitute the new world's controller/actors.
            if(!trigger_targets_.release(leases))return 3653;
            if(lease_&&!leases.release(lease_))return 3653;
            lease_=0;trigger_retirement_=RetirementPhase::Complete;
        }else if(!construction_.attempted){
            // The shared lifecycle intentionally does not own preallocation
            // dependencies. Retire these separately, never drop a GI holder.
            if(trigger_targets_.count&&(!trigger_context(b)||!helper_battle_quiescent(b)))return 407;
            if(!trigger_targets_.release(leases))return 3653;
        }else{
            struct Ops {
                Owner& owner;uint64_t base,session;Pool& pool;TriggerLeaseOps<Pool>& leases;
                bool current_context(){return owner.trigger_context(base);}
                bool battle_quiescent(){return owner.helper_battle_quiescent(base);}
                bool exact_owned_actor(){
                    return call_identity(base,owner.actor_)&&pool.owns_object(session,owner.lease_,owner.actor_.address)&&
                        local_read<uint64_t>(owner.actor_.address+16)==owner.ids_[4].address&&
                        owner.trigger_capture_components(base,session,pool);
                }
                bool unregister_owned_interactions_once(){
                    // Initial wrappers remain empty; original construction and
                    // refresh cannot register an interact action. EndPlay is
                    // responsible for the original component delegates.
                    return e33_trigger_anchor::safe_empty_instance(base,owner.actor_.address);
                }
                bool destroy_owned_actor_once(){
                    std::memset(owner.args_,0,sizeof(owner.args_));
                    return owner.call(base,2,owner.ids_[7],owner.actor_);
                }
                bool verify_original_endplay_and_all_registrations_absent(){
                    if(!current_context()||!call_identity(base,owner.actor_)||
                       !(local_read<uint8_t>(owner.actor_.address+0x5d)&1)||!owner.trigger_components_complete_)return false;
                    CallIdentity targets[8]{};size_t count=0;targets[count++]=owner.actor_;
                    for(size_t i=1;i<owner.trigger_targets_.count;++i)targets[count++]=owner.trigger_targets_.identities[i];
                    uint32_t total=0,owned=0;
                    return e33_npc_presentation::observe_listener_field(base,owner.trigger_targets_.identities[0],
                        e33_npc_presentation::listener_fields[0],targets,count,total,owned)&&owned==0&&current_context();
                }
                bool release_owned_lease_once(){
                    if(!current_context()||!battle_quiescent()||!owner.trigger_targets_.release(leases))return false;
                    if(!leases.release(owner.lease_))return false;
                    owner.lease_=0;return true;
                }
            } ops{*this,b,session,pool,leases};
            const auto result=retire(trigger_retirement_,true,ops);
            if(trigger_targets_.acquire_pending||trigger_targets_.release_pending||
               (trigger_capture_attempted_&&!trigger_components_complete_))return 3653;
            if(result!=RetirementResult::Complete)return result==RetirementResult::Deferred?407:3653;
        }
        // The original actor and every retained component survive until all
        // observations and releases above acknowledge completion.
        actor_={};owner_=0;attempted_=false;preparing_world_=false;construction_={};
        trigger_anchor_=false;trigger_targets_={};trigger_refresh_={};trigger_condition_={};trigger_serializable_={};
        trigger_capture_attempted_=trigger_components_complete_=trigger_ready_=false;
        trigger_refresh_attempted_=trigger_refresh_acknowledged_=trigger_actor_retention_pending_=false;
        trigger_retirement_=RetirementPhase::Ready;
        trigger_arena_pool_=nullptr;trigger_arena_session_=0;trigger_arena_cleanup_pending_=false;
        arena_binding_state_={};arena_binding_={};helper_entry_={};return 0;
    }
