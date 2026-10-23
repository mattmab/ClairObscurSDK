#pragma once
#include "npc_original_lifecycle_bridge.h"
#include "npc_current_context_guard.h"
#include "npc_clea_assembly_observation.h"
#include "npc_real_renoir_assembly_observation.h"
#include "npc_alicia_assembly_observation.h"
#include "npc_listener_observation.h"
#include "npc_component_lifecycle_policy.h"
#include "npc_grounded_preview.h"
#include "volume_query_profile.h"
#include "enemy_arena_engine_binding.h"
#include "helper_entry_lifetime.h"
#include "npc_interaction_profiles.h"
#include "npc_curator_assembly_observation.h"
#include "npc_curator_owned_interaction.h"
#include "npc_condition_graph_observation.h"
#include "npc_quest_listener_observation.h"
#include "npc_francois_assembly_observation.h"

namespace e33_npc_presentation {
struct CollisionVariant {uint32_t attempted=0,acknowledged=0,verified=0,before_mode=0,before_response=0,mode=0,response=0,actor_enabled=0;};
struct PreviewReveal {uint32_t attempted=0,acknowledged=0,observed=0,visible=0;};
// Bounded first original-NPC owner. Internal only until live preflight/packet
// validation is connected. No campaign actions, activation or encounter entry.
class CleaOwner {
    ConstructionSource source_{};ConstructionState state_{};RetirementBindings bindings_{};Lifecycle lifecycle_{};
    CallIdentity game_instance_{},condition_template_{};
    CallIdentity targets_[128]{};uint64_t target_leases_[128]{};size_t target_count_=0;
    uint32_t previous_guid_[4]{};bool owned_=false,targets_complete_=false,conditions_verified_=false;
    uint32_t unreviewed_script_components_=0;
    CallIdentity unexpected_controller_{};
    uint32_t step_=0;
    bool curator_=false;
    CuratorDialogueSource curator_source_{};
    InteractionIsolationJournal curator_interaction_{};
    InteractionIsolationJournal curator_postconstruction_{};
    GroundedPreview preview_{};
    PreviewReveal reveal_{};
    CollisionVariant collision_variant_{};
    e33_enemy_spawn::HelperEntryLifetime entry_lifetime_{};
    e33_enemy_spawn::EngineArenaBinding arena_binding_{};
    e33_enemy_spawn::ArenaBindingState arena_binding_state_{};
    CallIdentity arena_ids_[4]{};uint64_t arena_leases_[4]{};
    void* arena_pool_=nullptr;
    bool arena_requested_=false,arena_dependency_pending_=false,arena_value_closed_=false;
    uint32_t preview_result_=7; // 7 not requested, 6 unknown/in-flight
    bool preallocation_release_pending_=false;
    bool dependency_pending_=false;
    CleaAssemblyObservation assembly_{};MembershipObservation membership_{};ListenerObservation listeners_{};
    QuestListenerObservation quest_listeners_{};
    template<class Pool> bool retain_target(uint64_t base,uint64_t session,Pool& pool,uint64_t object){
        for(size_t i=0;i<target_count_;++i)if(targets_[i].address==object)return true;
        if(target_count_>=128)return false;
        auto& identity=targets_[target_count_];auto& lease=target_leases_[target_count_++];
        identity=call_capture(base,object);
        if(!identity.address)return false;
        TargetStrongReferenceOps ops{base,identity};
        return pool.acquire(ops,session,object,lease)==StrongLeaseResult::Ok&&stabilize_retained_identity(ops,identity);
    }
    template<class Pool> bool capture_targets(uint64_t base,uint64_t session,Pool& pool){
        if(target_count_)return false; // no replay after partial acquisition
        bool conditions=true;
        CallIdentity condition_components[8]{};size_t condition_count=0;
        const bool francois=francois_class(base,source_.actor_class);
        auto add=[&](uint64_t object){
            for(size_t i=0;i<target_count_;++i)if(targets_[i].address==object)return true;
            if(!retain_target(base,session,pool,object))return false;
            const auto identity=targets_[target_count_-1];
            const auto condition_class=local_read<uint64_t>(condition_template_.address+16);
            if(call_derives(base,local_read<uint64_t>(object+16),condition_class)&&!empty_condition_wrapper(base,identity)){
                conditions=false;
                if(francois){
                    if(condition_count>=8)return false;
                    condition_components[condition_count++]=identity;
                }
            }
            const auto cls=local_read<uint64_t>(object+16);
            if(object!=state_.actor.address&&exact_name(base,local_read<uint64_t>(cls+16)+24,"BlueprintGeneratedClass")&&
               !reviewed_component_class(base,cls))++unreviewed_script_components_;
            return true;
        };
        // Include native components as well as Blueprint-created components.
        // Independently retained identities survive original destruction long
        // enough for exact delegate-target cleanup observation.
        if(!add(state_.actor.address))return false;
        for(const auto spec:{std::pair<const char*,int>{"Mesh",792},{"CharacterMovement",800},{"CapsuleComponent",808}}){
            const auto at=picto_field(base,state_.actor.address,spec.first,"ObjectProperty",spec.second,8);
            if(!at||!local_read<uint64_t>(at)||!add(local_read<uint64_t>(at)))return false;
        }
        if(!e33_owned_actor::visit_components(base,state_.actor.address,add))return false;
        if(francois){
            // These nested UObjects are not ActorComponents. Keep their leases
            // in the same once-only journal, but do not misclassify them as
            // unreviewed script components. Admission remains a separate gate.
            auto retain_condition=[&](CallIdentity identity){return retain_target(base,session,pool,identity.address);};
            conditions=condition_count==3&&visit_francois_condition_roots(base,state_.actor,
                condition_components,condition_count,retain_condition);
        }
        targets_complete_=conditions;conditions_verified_=conditions;return conditions;
    }
    template<class Pool> struct Guard {
        CleaOwner& owner;uint64_t base,session;Pool& pool;
        bool current_context(){
            CurrentContextGuard context{base,owner.source_.controller,owner.source_.world};
            if(!context.current_context()||!call_identity(base,owner.game_instance_)||
               !e33_mesh::named(base,local_read<uint64_t>(owner.game_instance_.address+16),"BP_jRPG_GI_Custom_C",
                   "/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_GI_Custom"))return false;
            uint64_t descriptor=0;
            const auto at=picto_field(base,owner.source_.world.address,"OwningGameInstance","ObjectProperty",472,8,&descriptor);
            return at&&descriptor&&local_read<uint64_t>(descriptor)==base+0x6e11d38&&
                local_read<uint64_t>(descriptor+0x38)==0x14c001000002200ULL&&
                local_read<uint64_t>(at)==owner.game_instance_.address;
        }
        bool battle_quiescent(){
            return current_context()&&owner.entry_quiescent(base);
        }
        bool original_dialogue_isolation_contract(CallIdentity actor,CallIdentity dialog,CallIdentity available){
            return owner.curator_&&dialog.address==owner.curator_source_.dialog.address&&
                e33_npc_presentation::original_dialogue_isolation_contract(base,actor,dialog,available,owner.curator_source_.native_functions);
        }
        bool interaction_held(){
            if(!owner.curator_)return true;
            CuratorOwnedInteractionOps<Pool,Guard<Pool>> ops{base,session,owner.state_.actor_lease,pool,*this,
                owner.state_.actor,owner.curator_source_.dialog,owner.source_.available};
            return interaction_isolation_held(ops,owner.curator_postconstruction_.attempted?
                owner.curator_postconstruction_:owner.curator_interaction_);
        }
        bool verify_original_assembly_and_identity(CallIdentity actor,const uint32_t* guid){
            if(!current_context()||!battle_quiescent()||std::memcmp(guid,owner.previous_guid_,16)==0||
               !owner.capture_targets(base,session,pool))return false;
            const auto controller=picto_field(base,actor.address,"Controller","ObjectProperty",712,8);
            if(!controller)return false;
            const auto value=local_read<uint64_t>(controller);
            if(value){owner.unexpected_controller_=call_capture(base,value);return false;}
            const bool clea=e33_mesh::named(base,owner.source_.actor_class.address,"BP_JRPG_NPC_Dialog_NPC_MirrorClea_NoInteract_C",
                "/Game/Characters/Enemies/HumanEnnemies/Clea_v1/BP_JRPG_NPC_Dialog_NPC_MirrorClea_NoInteract");
            if(francois_class(base,owner.source_.actor_class)){
                if(!interaction_held()||!observe_francois_assembly(base,actor,owner.source_.actor_class,owner.assembly_))return false;
            }
            else if(owner.curator_){
                if(!interaction_held()||!observe_curator_assembly(base,actor,owner.source_.actor_class,owner.source_.cdo,owner.source_.available,owner.assembly_))return false;
            }
            else if(clea){if(!observe_clea_assembly(base,actor,owner.source_.actor_class,owner.source_.cdo,owner.source_.available,owner.assembly_))return false;}
            else if(!observe_real_renoir_assembly(base,actor,owner.source_.actor_class,owner.source_.cdo,owner.source_.available,owner.assembly_)&&
                    !observe_alicia_assembly(base,actor,owner.source_.actor_class,owner.source_.cdo,owner.source_.available,owner.assembly_))return false;
            std::memcpy(owner.previous_guid_,guid,16);return true;
        }
        bool verify_original_endplay_and_all_registrations_absent(CallIdentity actor){
            if(!current_context()||!battle_quiescent()||!owner.targets_complete_||!owner.conditions_verified_||
               owner.unreviewed_script_components_||owner.unexpected_controller_.address||
               !call_identity(base,actor)||!(local_read<uint8_t>(actor.address+0x5d)&1))return false;
            // The destruction bit is the existing SDK's verified native
            // IsActorBeingDestroyed getter storage. It alone is insufficient:
            // require original unregister/Destroy acknowledgements (Lifecycle)
            // plus absence of every owned actor/component target below.
            if(francois_class(base,owner.source_.actor_class)&&
               (!observe_quest_listeners(base,owner.game_instance_,owner.targets_,owner.target_count_,owner.quest_listeners_)||
                owner.quest_listeners_.owned))return false;
            return observe_memberships(base,owner.bindings_.interaction_system,owner.source_.controller,actor,owner.membership_)&&
                owner.membership_.absent()&&observe_listeners(base,owner.game_instance_,owner.targets_,owner.target_count_,owner.listeners_)&&
                owner.listeners_.absent();
        }
    };
    template<class Pool> struct Ops : OriginalLifecycleOps<Pool,Guard<Pool>> {
        CleaOwner& owner;
        Ops(uint64_t base,CleaOwner& value,uint64_t session,Pool& pool,Guard<Pool>& guard):
            OriginalLifecycleOps<Pool,Guard<Pool>>(base,value.source_,value.state_,pool,guard,value.bindings_),owner(value){(void)session;}
        bool prepare_private_instance(){
            if(!this->hold_private())return false;
            if(!owner.curator_)return true;
            CuratorOwnedInteractionOps<Pool,Guard<Pool>> isolate{this->base,this->source.session,this->state.actor_lease,
                this->pool,this->guard,this->state.actor,owner.curator_source_.dialog,this->source.available};
            return isolate_owned_interaction(isolate,owner.curator_interaction_)==InteractionIsolationResult::Complete;
        }
        bool finish_original_construction(){
            if(!OriginalLifecycleOps<Pool,Guard<Pool>>::finish_original_construction())return false;
            if(!owner.curator_)return true;
            CuratorOwnedInteractionOps<Pool,Guard<Pool>> isolate{this->base,this->source.session,this->state.actor_lease,
                this->pool,this->guard,this->state.actor,owner.curator_source_.dialog,this->source.available};
            // Original construction restores this instance flag. Re-isolate in
            // the same game-thread callback before returning to interaction
            // processing. This is a distinct journaled lifecycle assignment,
            // never a retry of the preconstruction write or a per-frame patch.
            if(interaction_isolation_held(isolate,owner.curator_interaction_))return true;
            return isolate_owned_interaction(isolate,owner.curator_postconstruction_)==InteractionIsolationResult::Complete;
        }
        bool release_owned_lease_once(){
            if(!this->current_context()||!this->battle_quiescent())return false;
            TargetStrongReferenceOps ops{this->base,{-1,0,0}};
            for(auto& lease:owner.arena_leases_){
                if(!lease)continue;
                if(this->pool.release(ops,this->source.session,lease)!=StrongLeaseResult::Ok)return false;
                lease=0;
            }
            for(size_t i=0;i<owner.target_count_;++i){
                auto& lease=owner.target_leases_[i];if(!lease)continue;
                if(this->pool.release(ops,this->source.session,lease)!=StrongLeaseResult::Ok)return false;
                lease=0;
            }
            return OriginalLifecycleOps<Pool,Guard<Pool>>::release_owned_lease_once();
        }
    };
#include "npc_clea_grounded_preview.inl"
#include "npc_clea_construction_placement.inl"
    void reset_after_cleanup(){
        uint32_t previous[4]{};std::memcpy(previous,previous_guid_,16);const auto step=step_;
        *this=CleaOwner{};std::memcpy(previous_guid_,previous,16);step_=step;
    }
public:
    bool has_work()const{return owned_;}
    const CollisionVariant& collision_variant()const{return collision_variant_;}
    // No dispatch authority is granted here. The once-only journal must be
    // persisted immediately before any future, separately authorized entry.
    template<class Pool> bool note_entry_dispatch(uint64_t base,uint64_t session,Pool& pool,
            const CallIdentity& actor,const CallIdentity& manager,const CallIdentity& function){
        uint64_t name=0;
        return owned_entry_context(base,session,pool,actor,manager,function,name)&&entry_lifetime_.begin(name);
    }
    bool entry_quiescent(uint64_t base){
        CurrentContextGuard context{base,source_.controller,source_.world};
        e33_battle_state::Observation observation{};
        if(!context.observe_battle(observation))return false;
        const auto arena=arena_ids_[0];
        const bool own_active=entry_lifetime_.pending()&&observation.started&&observation.enemy_count>0&&
            observation.encounter_name==entry_lifetime_.name()&&call_identity(base,arena)&&observation.arena==arena.address;
        entry_lifetime_.observe(own_active,observation.idle());
        return observation.idle()&&entry_lifetime_.ready();
    }
    void poll_entry(uint64_t base){if(entry_lifetime_.pending())(void)entry_quiescent(base);}
    e33_enemy_spawn::HelperEntryPhase entry_phase()const{return entry_lifetime_.phase();}
    const ConstructionState& state()const{return state_;}
    const Lifecycle& lifecycle()const{return lifecycle_;}
    const CleaAssemblyObservation& assembly()const{return assembly_;}
    uint32_t unreviewed_script_components()const{return unreviewed_script_components_;}
    size_t retained_target_count()const{return target_count_;}
    CallIdentity unexpected_controller()const{return unexpected_controller_;}
    uint32_t step()const{return step_;}
    const GroundedPreview& preview()const{return preview_;}
    uint32_t preview_result()const{return preview_result_;}
    const PreviewReveal& reveal_status()const{return reveal_;}
    const e33_enemy_spawn::ArenaBindingState& arena_state()const{return arena_binding_state_;}
    bool arena_requested()const{return arena_requested_;}
    size_t arena_lease_count()const{size_t count=0;for(auto lease:arena_leases_)if(lease)++count;return count;}
    CallIdentity bound_arena()const{return arena_ids_[0];}
#include "npc_clea_parameter_entry.inl"
    // Read-only approach observation. Reuse the same exact current-pawn and
    // engine location profiles as grounded placement; no actor movement.
    template<class Pool> uint32_t observe_proximity(uint64_t base,uint64_t session,Pool& pool,
            const CallIdentity (&query)[10],double (&out)[7]){
        uint64_t name=0;
        if(!owned_parameter_instance_name(base,session,pool,state_.actor,name)||!reveal_.visible)return 3496;
        PreviewOps<Pool> ops{*this,base,session,pool,query};
        double player[3]{},actor[3]{};
        if(!ops.get(5,3,query[0],player)||!ops.location(actor)||!ops.current())return 3496;
        double squared=0;
        for(unsigned i=0;i<3;++i){
            if(!std::isfinite(player[i])||!std::isfinite(actor[i]))return 3496;
            const auto delta=player[i]-actor[i];squared+=delta*delta;
        }
        if(!std::isfinite(squared))return 3496;
        out[0]=squared;std::memcpy(out+1,player,24);std::memcpy(out+4,actor,24);return 0;
    }
#include "npc_clea_interaction_variants.inl"
    template<class Pool> uint32_t bind_preview_arena(uint64_t base,uint64_t session,Pool& pool,const CallIdentity (&query)[4]){
        if(arena_requested_)return 3491;
        uint64_t name=0;
        if(!owned_parameter_instance_name(base,session,pool,state_.actor,name)||pool.preflight(session,4)!=StrongLeaseResult::Ok)return 3490;
        for(const auto& id:query)if(!call_identity(base,id))return 3490;
        arena_requested_=true;arena_pool_=&pool;std::memcpy(arena_ids_,query,sizeof(arena_ids_));
        auto configure=[&](){
            arena_binding_.configure_owned_presentation_value(base,source_.world.address,state_.actor,
                arena_ids_[0],arena_ids_[1],arena_ids_[2],arena_ids_[3],this,
                [](void* context,uint64_t b,const CallIdentity& actor,uint64_t world){
                    auto& held=*static_cast<CleaOwner*>(context);uint64_t instance=0;
                    return world==held.source_.world.address&&held.arena_pool_&&
                        held.owned_parameter_instance_name(b,held.source_.session,*static_cast<Pool*>(held.arena_pool_),actor,instance);
                });
        };
        configure();if(!arena_binding_.preflight())return 3490;
        for(unsigned i=0;i<4;++i){
            arena_dependency_pending_=true;
            TargetStrongReferenceOps refs{base,arena_ids_[i]};
            if(pool.acquire(refs,session,arena_ids_[i].address,arena_leases_[i])!=StrongLeaseResult::Ok||
               !stabilize_retained_identity(refs,arena_ids_[i]))return 3492;
            arena_dependency_pending_=false;
        }
        configure();
        return e33_enemy_spawn::bind_owned_arena(arena_binding_,arena_binding_state_)==e33_enemy_spawn::ArenaBindingResult::Ok?0:3493;
    }
    // Shared battle-parameter policy callback. This proves only the name of a
    // retained, fully assembled grounded NPC. It grants no arena or dispatch
    // authority and does not impersonate an EnemySpawner owner.
    template<class Pool> bool owned_parameter_instance_name(uint64_t base,uint64_t session,Pool& pool,
            const CallIdentity& observed,uint64_t& name){
        name=0;
        if(!owned_||session!=source_.session||!preview_.verified||!preview_.at_construction||
           lifecycle_.construction().phase!=e33_owned_actor::ConstructionPhase::Complete||
           lifecycle_.retirement()!=RetirementPhase::Ready||!targets_complete_||!conditions_verified_||
           unreviewed_script_components_||unexpected_controller_.address||
           (collision_variant_.attempted&&!collision_variant_.verified)||
           observed.index!=state_.actor.index||observed.serial!=state_.actor.serial||observed.address!=state_.actor.address||
           (reveal_.attempted&&(!reveal_.acknowledged||!reveal_.observed||!reveal_.visible)))return false;
        Guard<Pool> guard{*this,base,session,pool};Ops<Pool> ops(base,*this,session,pool,guard);
        if(!ops.exact_owned_actor()||!guard.battle_quiescent()||!guard.interaction_held()||!plan_defaults_unchanged(base)||
           exact_name(base,state_.actor.address+24,"None"))return false;
        CleaAssemblyObservation checked{};
        if(francois_class(base,source_.actor_class)){
            if(!observe_francois_assembly(base,state_.actor,source_.actor_class,checked))return false;
        }else if(curator_){
            if(!observe_curator_assembly(base,state_.actor,source_.actor_class,source_.cdo,source_.available,checked))return false;
        }else if(!observe_clea_assembly(base,state_.actor,source_.actor_class,source_.cdo,source_.available,checked)&&
                 !observe_alicia_assembly(base,state_.actor,source_.actor_class,source_.cdo,source_.available,checked))return false;
        name=local_read<uint64_t>(state_.actor.address+24);return name!=0;
    }
    template<class Pool> uint32_t reveal_preview(uint64_t base,uint64_t session,Pool& pool){
        if(reveal_.attempted)return 3481;
        if(!owned_||session!=source_.session||!preview_.verified||!preview_.at_construction||
           lifecycle_.construction().phase!=e33_owned_actor::ConstructionPhase::Complete||
           lifecycle_.retirement()!=RetirementPhase::Ready||!targets_complete_||!conditions_verified_||
           unreviewed_script_components_||unexpected_controller_.address)return 3480;
        Guard<Pool> guard{*this,base,session,pool};Ops<Pool> ops(base,*this,session,pool,guard);
        if(!ops.exact_owned_actor()||!guard.battle_quiescent()||!guard.interaction_held()||!plan_defaults_unchanged(base))return 3480;
        const auto collision=component_field(base,state_.actor.address,"bActorEnableCollision","BoolProperty",92,1,"Actor",0x6e119b0,0x48001000000000ULL);
        uint64_t hidden_descriptor=0;
        const auto hidden=picto_field(base,state_.actor.address,"bHidden","BoolProperty",88,1,&hidden_descriptor);
        if(!collision||!hidden||!hidden_descriptor||local_read<uint32_t>(hidden_descriptor+0x70)!=0x80800001U||
           !component_field(base,state_.actor.address,"bHidden","BoolProperty",88,1,"Actor",0x6e119b0,0x48001200000035ULL)||
           (local_read<uint8_t>(collision)&0x80)||!(local_read<uint8_t>(hidden)&0x80))return 3480;
        const auto capsule_at=picto_field(base,state_.actor.address,"CapsuleComponent","ObjectProperty",808,8);
        const auto capsule=capsule_at?local_read<uint64_t>(capsule_at):0;
        const auto location=capsule?picto_field(base,capsule,"RelativeLocation","StructProperty",296,24):0;
        const auto parent=capsule?picto_field(base,capsule,"AttachParent","ObjectProperty",176,8):0;
        if(!location||!parent||local_read<uint64_t>(parent))return 3480;
        for(unsigned i=0;i<3;++i)if(!std::isfinite(local_read<double>(location+i*8))||
            std::abs(local_read<double>(location+i*8)-preview_.destination[i])>.1)return 3480;
        CleaAssemblyObservation checked{};
        const bool clea=e33_mesh::named(base,source_.actor_class.address,"BP_JRPG_NPC_Dialog_NPC_MirrorClea_NoInteract_C",
            "/Game/Characters/Enemies/HumanEnnemies/Clea_v1/BP_JRPG_NPC_Dialog_NPC_MirrorClea_NoInteract");
        if(francois_class(base,source_.actor_class)){if(!observe_francois_assembly(base,state_.actor,source_.actor_class,checked))return 3480;}
        else if(curator_){if(!observe_curator_assembly(base,state_.actor,source_.actor_class,source_.cdo,source_.available,checked))return 3480;}
        else if(clea){if(!observe_clea_assembly(base,state_.actor,source_.actor_class,source_.cdo,source_.available,checked))return 3480;}
        else if(!observe_real_renoir_assembly(base,state_.actor,source_.actor_class,source_.cdo,source_.available,checked)&&
                !observe_alicia_assembly(base,state_.actor,source_.actor_class,source_.cdo,source_.available,checked))return 3480;
        std::memset(state_.arguments,0,sizeof(state_.arguments));
        reveal_.attempted=1;
        if(!ops.engine(source_.hidden,state_.actor,e33_actor_visibility::hidden))return 3482;
        reveal_.acknowledged=1;
        if(!ops.exact_owned_actor()||!guard.battle_quiescent()||!guard.interaction_held())return 3483;
        reveal_.observed=1;reveal_.visible=(local_read<uint8_t>(hidden)&0x80)?0:1;
        return reveal_.visible?0:3483;
    }
    // Internal candidate path only. No research wire operation or activation
    // exposes this until the exact source preparation is connected and tested.
    template<class Pool> PreviewPlacementResult place_preview_grounded(uint64_t base,uint64_t session,Pool& pool,
            const CallIdentity (&query)[10]){
        PreviewOps<Pool> ops{*this,base,session,pool,query};
        if(preview_.placement.attempted)return PreviewPlacementResult::AlreadyAttempted;
        preview_result_=6;
        const auto result=place_preview(ops,preview_);
        preview_result_=uint32_t(result);return result;
    }
    template<class Pool> uint32_t stage(uint64_t base,uint64_t session,Pool& pool,const ConstructionSource& source,
            const RetirementBindings& bindings,CallIdentity game_instance,CallIdentity condition_template,const CallIdentity* grounding=nullptr){
        if(owned_)return 3430;
        step_=1;
        if(!session||source.class_lease||source.cdo_lease)return 3431;
        CuratorDialogueSource curator_source{};
        const bool curator=curator_source_contract(base,source.actor_class,source.cdo,source.available,curator_source);
        const bool francois=francois_source_contract(base,source.actor_class,source.cdo,source.available,curator_source);
        if(!presentation_class_contract(base,source.actor_class,source.cdo,source.available)||
           !(curator||francois||e33_mesh::named(base,source.actor_class.address,"BP_JRPG_NPC_Dialog_NPC_MirrorClea_NoInteract_C",
               "/Game/Characters/Enemies/HumanEnnemies/Clea_v1/BP_JRPG_NPC_Dialog_NPC_MirrorClea_NoInteract")||
             e33_mesh::named(base,source.actor_class.address,"BP_JRPG_NPC_Dialog_NPC_RealRenoir_NoInteract_C",
               "/Game/Characters/Enemies/HumanEnnemies/Real_Renoir/BP_JRPG_NPC_Dialog_NPC_RealRenoir_NoInteract")||
             e33_mesh::named(base,source.actor_class.address,"BP_JRPG_NPC_Dialog_NPC_MirrorAlicia_NoInteract_C",
               "/Game/Characters/Enemies/HumanEnnemies/Alicia/BP_JRPG_NPC_Dialog_NPC_MirrorAlicia_NoInteract"))||
           !call_identity(base,condition_template)||
           !exact_name(base,condition_template.address+24,"BP_ConditionCheckerComponent_GEN_VARIABLE")||
           !e33_mesh::named(base,local_read<uint64_t>(condition_template.address+32),"BP_jRPG_NPC_Dialog_C",
               "/Game/LevelTools/NPCs/BP_jRPG_NPC_Dialog")||
           !call_derives(base,source.actor_class.address,local_read<uint64_t>(condition_template.address+32))||
           !empty_condition_wrapper(base,condition_template)||!original_clea_possession_defaults(base,source.cdo.address))return 3431;
        source_=source;source_.session=session;bindings_={};curator_=curator||francois;curator_source_=curator_source;
        bindings_.interaction_system=bindings.interaction_system;bindings_.unregister_nearby=bindings.unregister_nearby;
        bindings_.unregister_distant=bindings.unregister_distant;
        game_instance_=game_instance;condition_template_=condition_template;
        Guard<Pool> guard{*this,base,session,pool};
        step_=2;
        if(!guard.current_context()||!guard.battle_quiescent()){reset_after_cleanup();return 3432;}
        ListenerObservation preflight{};
        step_=3;
        if(!observe_listeners(base,game_instance_,&source_.controller,1,preflight)){reset_after_cleanup();return 3432;}
        if(francois&&!observe_quest_listeners(base,game_instance_,&source_.controller,1,quest_listeners_)){
            reset_after_cleanup();return 3432;
        }
        MembershipObservation registration_preflight{};
        step_=4;
        const auto system_class=call_identity(base,bindings_.interaction_system)?local_read<uint64_t>(bindings_.interaction_system.address+16):0;
        if(!observe_memberships(base,bindings_.interaction_system,source_.controller,source_.controller,registration_preflight)||
           !unregister_function_contract(base,bindings_.unregister_nearby,system_class,unregister_profile_0)||
           !unregister_function_contract(base,bindings_.unregister_distant,system_class,unregister_profile_1)){
            reset_after_cleanup();return 3432;
        }
        // Reject missing/changed native profiles before any actor allocation.
        // Validation performs no ProcessEvent and does not exercise a CDO.
        auto profile_valid=[&](CallIdentity function,CallIdentity recipient,const MeshFunction& profile){
            e33_engine_profile_call::TargetOps call{base,call_identity(base,function),call_identity(base,recipient),profile,nullptr};
            return call.context()&&call.identities()&&call.exact_profile()&&call.recipient_derives()&&call.dispatch_entry();
        };
        const auto movement_at=picto_field(base,source_.cdo.address,"CharacterMovement","ObjectProperty",800,8);
        step_=5;
        if(!movement_at||!profile_valid(source_.begin,source_.gameplay_statics,e33_engine_profiles::profiles[0])||
           !profile_valid(source_.finish,source_.gameplay_statics,e33_engine_profiles::profiles[1])||
           !profile_valid(source_.destroy,source_.cdo,e33_engine_profiles::profiles[2])||
           !profile_valid(source_.collision,source_.cdo,e33_engine_profiles::profiles[47])||
           !profile_valid(source_.tick,source_.cdo,e33_engine_profiles::profiles[58])||
           !profile_valid(source_.hidden,source_.cdo,e33_actor_visibility::hidden)||
           !profile_valid(source_.movement,call_capture(base,local_read<uint64_t>(movement_at)),e33_engine_profiles::profiles[10])){
            reset_after_cleanup();return 3432;
        }
        step_=6;
        if(pool.preflight(session,131)!=StrongLeaseResult::Ok){reset_after_cleanup();return 3433;}
        owned_=true; // persistent before any lease acquisition or construction
        for(const auto entry:{std::pair<CallIdentity*,uint64_t*>{&source_.actor_class,&source_.class_lease},{&source_.cdo,&source_.cdo_lease}}){
            dependency_pending_=true;
            TargetStrongReferenceOps ops{base,*entry.first};
            if(pool.acquire(ops,session,entry.first->address,*entry.second)!=StrongLeaseResult::Ok||
               !stabilize_retained_identity(ops,*entry.first))return 3433;
            dependency_pending_=false;
        }
        Ops<Pool> ops(base,*this,session,pool,guard);
        if(grounding){
            CallIdentity queries[10]{};std::memcpy(queries,grounding,sizeof(queries));
            ConstructionPlacementOps<Pool> plan{*this,base,session,pool,queries};
            preview_result_=6;
            const auto result=place_preview(plan,preview_,true);preview_result_=uint32_t(result);
            if(result!=PreviewPlacementResult::Complete)return 3470+uint32_t(result);
            preview_.at_construction=true;std::memcpy(source_.transform+4,preview_.destination,24);
        }
        step_=7;
        const auto result=lifecycle_.stage(ops);
        if(result==StageResult::Complete)step_=8;
        if(result==StageResult::Complete&&grounding){
            CallIdentity queries[10]{};std::memcpy(queries,grounding,sizeof(queries));
            PreviewOps<Pool> observation{*this,base,session,pool,queries};
            PreviewBounds bounds{};e33_actor_pose::Pose actual{};
            if(!e33_actor_pose::observe(observation,actual)||!observation.bounds(false,bounds))return 3476;
            preview_.placement.after=actual;preview_.placement.readback=true;
            for(unsigned i=0;i<3;++i)if(std::abs(actual.location[i]-preview_.destination[i])>.1||
                std::abs(bounds.center[i]-preview_.destination[i])>.1)return 3476;
            if(!e33_actor_pose::same_rotation(actual.rotation,preview_.placement.before.rotation,.001)||
               !plan_defaults_unchanged(base))return 3476;
            preview_.verified=true;
        }
        return result==StageResult::Complete?0:3434;
    }
    template<class Pool> uint32_t close(uint64_t base,uint64_t session,Pool& pool){
        if(!owned_)return 0;
        if(session!=source_.session)return 3435;
        if(preallocation_release_pending_||dependency_pending_||arena_dependency_pending_)return 3438;
        Guard<Pool> guard{*this,base,session,pool};
        if(!guard.current_context()||!guard.battle_quiescent())return 3436;
        if(arena_requested_&&!arena_value_closed_){
            if(!e33_enemy_spawn::close_arena_binding_temporary(arena_binding_,arena_binding_state_)||!arena_binding_.close_owned_value())return 3494;
            arena_value_closed_=true;
        }
        Ops<Pool> ops(base,*this,session,pool,guard);
        if(!lifecycle_.construction().attempted){
            // Known preallocation rejection/dependency failure. No actor was
            // attempted; release only this owner's acknowledged dependencies.
            preallocation_release_pending_=true;
            if(!ops.release_owned_lease_once())return 3437;
            reset_after_cleanup();return 0;
        }
        // A Curator isolation failure may precede FinishSpawning and the normal
        // postconstruction inventory. Observe/retain the exact existing owned
        // components before destruction; never replay partial acquisitions.
        if(curator_&&!targets_complete_){
            if(target_count_||!ops.exact_owned_actor()||!capture_targets(base,session,pool))return 3439;
        }
        const auto result=lifecycle_.retire(ops);
        if(result!=RetirementResult::Complete)return result==RetirementResult::UnknownOutcome?3438:3439;
        reset_after_cleanup();return 0;
    }
};
}
