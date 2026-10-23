#pragma once
#include "engine_profiles.h"
#include "validated_engine_profile_call.h"
#include "actor_visibility_profile.h"
#include "stable_identity.h"
#include "numbered_field_name.h"
#include "enemy_world_policy.h"
#include "enemy_retirement.h"
#include "helper_retirement.h"
#include "helper_entry_lifetime.h"
#include "geometry_bounds.h"
#include "authored_encounter_override.h"
#include "enemy_arena_assembly.h"
#include "enemy_arena_engine_binding.h"
#include "enemy_extra_spots_engine.h"
#include "actor_pose_operations.h"
#include "owned_actor_construction.h"
#include "owned_component_visit.h"
#include "battle_quiescence_observation.h"
#include "enemy_combat_placement_policy.h"
#include "enemy_ground_search.h"
#include "volume_query.h"
#include "volume_query_profile.h"
#include "component_transform_profiles.h"
#include "component_pose_policy.h"
#include "helper_parameter_anchor.h"
#include "arena_ground_report.h"
#include "arena_approach_policy.h"
#include "helper_source_frame.h"
#include "owned_actor_retirement.h"
#include "trigger_anchor_journal.h"
#include "trigger_anchor_profile.h"
#include "retired_owned_actor.h"
#include "npc_listener_observation.h"
#pragma warning(push)
#pragma warning(disable:4324)
// Owned enemy adapter for the current Cinematics candidate. Reuses native profiles;
// no general reflection codecs, CDO/table edits or arbitrary classes.
namespace e33_enemy_spawn {
using namespace e33_mesh;
#include "enemy_world_recipes.inl"
#ifdef E33_ENEMY_VISUAL_RESEARCH
#include "enemy_visual_recipes.inl"
#endif
class Owner {
    bool arena_staging_=false;
    void* trigger_arena_pool_=nullptr;uint64_t trigger_arena_session_=0;
    bool trigger_arena_cleanup_pending_=false;
    bool trigger_anchor_=false,trigger_capture_attempted_=false,trigger_components_complete_=false;
    bool trigger_ready_=false,trigger_refresh_attempted_=false,trigger_refresh_acknowledged_=false,trigger_actor_retention_pending_=false;
    CallIdentity trigger_refresh_{},trigger_condition_{},trigger_serializable_{};
    e33_trigger_anchor::RetainedTargets<CallIdentity> trigger_targets_{};
    e33_owned_actor::RetirementPhase trigger_retirement_=e33_owned_actor::RetirementPhase::Ready;
    CallIdentity component_pose_targets_[32]{};
    bool arena_ground_attempted_=false,arena_grounded_=false;
    e33_actor_pose::Placement arena_ground_journal_{};
    CallIdentity arena_ground_frame_function_{},arena_ground_rotation_function_{};
    CallIdentity ids_[12]{},actor_{};uint64_t lease_=0,owner_=0;bool attempted_=false,initialized_=false,placement_attempted_=false;
    EngineArenaBinding arena_binding_{};ArenaBindingState arena_binding_state_{};
    ExtraSpotsEngineState extra_spots_{};
    bool preparing_world_=false,grounded_=false;
    HelperEntryLifetime helper_entry_{};
    e33_owned_actor::ConstructionJournal construction_{};
    AuthoredEncounterOverride encounter_override_{};CallIdentity encounter_table_{},authored_cdo_{};uint64_t authored_cdo_lease_=0;
    CallIdentity movement_{},movement_function_{};uint8_t movement_mode_=0,movement_custom_=0;
    alignas(16) uint8_t args_[464]{};
    template<class T> void put(size_t at,T v){std::memcpy(args_+at,&v,sizeof(v));}
    bool call(uint64_t b,size_t profile,CallIdentity fnid,CallIdentity recipient){
        static const MeshField lookup_fields[]={
            {"WorldContextObject","ObjectProperty",0,8,0x18001000000282ULL,0x6e11d38ULL,"","",0,"",0U,"Object"},
            {"ActorClass","ClassProperty",8,8,0x1c001000000280ULL,0x6e12ac8ULL,"","",0,"",0U,"Actor"},
            {"ReturnValue","ObjectProperty",16,8,0x18001000000780ULL,0x6e11d38ULL,"","",0,"",0U,"Actor"}};
        static const MeshFunction lookup={"GameplayStatics","GetActorOfClass",0x4022403,24,24,16,0x3737c40,lookup_fields,3};
        const auto& p=profile==102?lookup:(profile==101?e33_volume_query::box_profile:(profile==100?e33_actor_visibility::hidden:e33_engine_profiles::profiles[profile]));
        return e33_engine_profile_call::invoke(b,fnid,recipient,p,args_);
    }
#include "enemy_grounded_placement.inl"
    bool visual_class(uint64_t b)const{
        if(arena_staging_){
            for(auto cls=ids_[4].address,walked=uint64_t(0);cls&&walked<64;++walked,cls=local_read<uint64_t>(cls+0x40)){
                if(!call_identity(b,call_capture(b,cls))||!call_is_class(b,cls))return false;
                if(named(b,cls,"BP_BattleMap_C","/Game/Levels/Battle_Maps/BP_BattleMap"))return true;
            }
            return false;
        }
#ifdef E33_ENEMY_VISUAL_RESEARCH
        for(const auto& row:enemy_visual_recipes)if(named(b,ids_[4].address,row[0],row[1]))return true;
#else
        (void)b;
#endif
        return false;
    }
    bool source_current(uint64_t b,bool prepare_or_read_only=false){
        if(!TargetPodSchemaOps{b}.context())return false;
        // Combat unpossesses the exploration pawn. World/controller/source
        // authority is independent of a pawn-specific staging observation.
        for(unsigned i=0;i<12;++i)if(i!=1&&!call_identity(b,ids_[i]))return false;
        bool recipe=false;
        for(const auto& row:enemy_world_recipes)if(named(b,ids_[4].address,row[0],row[1])){recipe=true;break;}
        #ifdef E33_ENEMY_VISUAL_RESEARCH
        for(const auto& row:enemy_visual_recipes)if(named(b,ids_[4].address,row[0],row[1])){recipe=true;break;}
        #endif
        if(arena_staging_)recipe=visual_class(b);
        if(trigger_anchor_)recipe=!arena_staging_&&e33_trigger_anchor::exact_class(b,ids_[4].address);
        if(!world_path_allowed(named(b,ids_[2].address,"Map_BattleTesting","/Game/QA/Map_BattleTesting"),owner_&&attempted_&&preparing_world_,prepare_or_read_only)||
           !named(b,local_read<uint64_t>(ids_[2].address+16),"World","/Script/Engine")||
           !recipe||
           !call_is_class(b,ids_[4].address)||!named(b,ids_[3].address,"Default__GameplayStatics","/Script/Engine"))return false;
        bool pc=false;
        auto o=ids_[0].address;for(int i=0;o&&i<32;++i,o=local_read<uint64_t>(o+32)){if(o==ids_[2].address){pc=true;break;}}
        return pc;
    }
    bool current(uint64_t b,bool prepare_or_read_only=false){
        if(!source_current(b,prepare_or_read_only)||!call_identity(b,ids_[1]))return false;
        bool pawn=false;
        auto o=ids_[1].address;
        for(int i=0;o&&i<32;++i,o=local_read<uint64_t>(o+32)){if(o==ids_[2].address){pawn=true;break;}}
        if(!pawn)return false;
        std::memset(args_,0,sizeof(args_));
        return call(b,21,ids_[8],ids_[0])&&local_read<uint64_t>(reinterpret_cast<uint64_t>(args_))==ids_[1].address;
    }
    bool entry_source_current(uint64_t b,bool visual){
        struct Ops{
            Owner& owner;uint64_t base;
            bool source_current(){return owner.source_current(base,true);}
            bool pawn_current(){return owner.current(base);}
        } ops{*this,b};
        return helper_entry_source_context(ops,visual);
    }
#include "enemy_combat_placement.inl"
#include "enemy_owned_components.inl"
#include "enemy_helper_retirement.inl"
#include "enemy_authored_encounter.inl"
#include "enemy_trigger_anchor.inl"
public:
    explicit Owner(bool arena_staging=false):arena_staging_(arena_staging){}
    bool has_work()const{return owner_||lease_;}
    bool is_trigger_anchor()const{return trigger_anchor_;}
    CallIdentity staged_actor()const{return actor_;}
    bool token_matches(uint64_t token)const{return !owner_||owner_==token;}
#include "owned_arena_component_pose.inl"
#include "owned_arena_grounding.inl"
#include "owned_arena_helper_qualification.inl"
    template<class Pool> bool note_entry_dispatch(uint64_t b,uint64_t session,Pool& pool,uint64_t token,
        const CallIdentity& actor,const CallIdentity& manager,const CallIdentity& function){
        if(trigger_anchor_)return false; // v194 permits copying/binding only, never dispatch.
        uint64_t name=0;
        if(!grounded_||!arena_binding_state_.verified||
           !owned_entry_context(b,session,pool,token,actor,manager,function,name))return false;
        return helper_entry_.begin(name); // persisted immediately before ProcessEvent
    }
    template<class Pool> bool trigger_dispatch_arena_ready(uint64_t b,uint64_t session,Pool& pool,
            const CallIdentity& expected,uint64_t world,uint64_t controller){
        if(!arena_staging_||trigger_anchor_||!owner_||!lease_||!arena_grounded_||!arena_ground_attempted_||
           !arena_ground_journal_.attempted||!arena_ground_journal_.acknowledged||
           !arena_ground_journal_.engine_accepted||!arena_ground_journal_.readback||
           construction_.phase!=e33_owned_actor::ConstructionPhase::Complete||
           helper_entry_.phase()!=HelperEntryPhase::Empty||ids_[2].address!=world||ids_[0].address!=controller||
           expected.index!=actor_.index||expected.serial!=actor_.serial||expected.address!=actor_.address||
           !current(b,true)||!helper_battle_quiescent(b)||!call_identity(b,actor_)||
           !pool.owns_object(session,lease_,actor_.address)||!arena_live(b,actor_.address))return false;
        ArenaAssemblyObservation assembly{};
        if(observe_arena_assembly(b,world,actor_.address,assembly)||assembly.streaming_enabled)return false;
        uint64_t hd=0,cd=0;
        const auto hidden=picto_field(b,actor_.address,"bHidden","BoolProperty",88,1,&hd);
        const auto collision=picto_field(b,actor_.address,"bActorEnableCollision","BoolProperty",92,1,&cd);
        if(!hidden||!hd||!collision||!cd||local_read<uint32_t>(hd+0x70)!=0x80800001U||
           local_read<uint32_t>(cd+0x70)!=0x80800001U||!(local_read<uint8_t>(hidden)&0x80)||
           (local_read<uint8_t>(collision)&0x80))return false;
        const auto root=arena_reference(b,actor_.address,"RootComponent",416);
        const auto parent=root?picto_field(b,root,"AttachParent","ObjectProperty",176,8):0;
        if(!root||!parent||local_read<uint64_t>(parent)||!arena_scene(b,root,actor_.address))return false;
        std::memset(args_,0,sizeof(args_));
        if(!call(b,19,arena_ground_frame_function_,call_capture(b,root)))return false;
        double pose[12]{};std::memcpy(pose,args_,96);pose[7]=pose[11]=0;
        if(!unit_yaw_frame(pose,1.e7))return false;
        for(unsigned i=0;i<3;++i)if(std::abs(pose[4+i]-arena_ground_journal_.after.location[i])>.1)return false;
        std::memset(args_,0,sizeof(args_));
        if(!call(b,4,arena_ground_rotation_function_,actor_))return false;
        double angles[3]{};std::memcpy(angles,args_,24);
        return e33_actor_pose::same_rotation(angles,arena_ground_journal_.after.rotation,.001)&&
            current(b,true)&&helper_battle_quiescent(b)&&call_identity(b,actor_)&&
            pool.owns_object(session,lease_,actor_.address);
    }
    template<class Pool> bool note_trigger_entry_dispatch(uint64_t b,uint64_t session,Pool& pool,uint64_t token,
            const CallIdentity& actor,const CallIdentity& manager,const CallIdentity& function,Owner& arena){
        uint64_t name=0;CallIdentity bound{};
        if(!trigger_anchor_||arena_staging_||helper_entry_.phase()!=HelperEntryPhase::Empty||
           !owned_entry_context(b,session,pool,token,actor,manager,function,name)||
           !owned_entry_arena(b,session,pool,token,actor,bound)||
           !arena.trigger_dispatch_arena_ready(b,session,pool,bound,ids_[2].address,ids_[0].address))return false;
        // The existing entry callback runs immediately before ProcessEvent.
        // Reserve both lifetimes first; unknown startup never permits retirement.
        // No trigger body, reveal, movement or fabricated grounded_ bit is used.
        if(!helper_entry_.begin(name))return false;
        return arena.helper_entry_.begin(name);
    }

    void poll_helper_entry(uint64_t b){
        if(helper_entry_.pending())(void)helper_battle_quiescent(b);
    }
    template<class Pool> bool owned_entry_arena(uint64_t b,uint64_t session,Pool& pool,
        uint64_t token,const CallIdentity& observed,CallIdentity& arena){
        uint64_t name=0;
        if(!owned_instance_name(b,session,pool,token,observed,name)||!arena_binding_state_.verified)return false;
        arena=arena_binding_.observed_arena();ArenaAssemblyObservation assembly{};
        return call_identity(b,arena)&&!observe_arena_assembly(b,ids_[2].address,arena.address,assembly)&&
            arena_binding_.preflight()&&arena_binding_.dependencies_supported();
    }
    template<class Pool> bool copy_entry_arena(uint64_t b,uint64_t session,Pool& pool,
        uint64_t token,const CallIdentity& observed,const CallIdentity& expected,void* destination){
        CallIdentity arena{};
        if(!owned_entry_arena(b,session,pool,token,observed,arena)||
           arena.index!=expected.index||arena.serial!=expected.serial||arena.address!=expected.address)return false;
        arena_binding_state_.temporary_live=true;
        if(!arena_binding_.copy_soft_reference(destination)||!arena_binding_.verify_soft_reference(destination))return false;
        return close_arena_binding_temporary(arena_binding_,arena_binding_state_);
    }
    template<class Pool> bool owned_entry_context(uint64_t b,uint64_t session,Pool& pool,
        uint64_t token,const CallIdentity& observed,const CallIdentity& manager,const CallIdentity& function,uint64_t& name){
#if E33_RUNTIME_CINEMATIC_VERSION < 195
        if(trigger_anchor_)return false;
#endif
        if(!owned_instance_name(b,session,pool,token,observed,name)||
           !call_identity(b,manager)||!call_identity(b,function)||
           local_read<uint64_t>(manager.address+32)!=ids_[0].address||
           !arena_class(b,manager.address,"AC_jRPG_BattleManager_C","/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_BattleManager")||
           local_read<uint64_t>(function.address+32)!=local_read<uint64_t>(manager.address+16)||
           !exact_name(b,function.address+24,"StartBattleNEW"))return false;
        const auto initialized=picto_field(b,manager.address,"IsBattleInitialized","BoolProperty",168,1);
        const auto ending=picto_field(b,manager.address,"HasBattleStartedEndFlow","BoolProperty",1961,1);
        const auto enemies=picto_field(b,manager.address,"Enemies","ArrayProperty",200,16);
        return initialized&&ending&&enemies&&!local_read<uint8_t>(initialized)&&!local_read<uint8_t>(ending)&&
            local_read<int32_t>(enemies+8)==0;
    }
    template<class Pool> bool owned_instance_name(uint64_t b,uint64_t session,Pool& pool,
        uint64_t token,const CallIdentity& observed,uint64_t& name) {
        if(trigger_anchor_)return trigger_parameter_name(b,session,pool,token,observed,name);
        const bool visual=visual_class(b);
        if((!visual&&!initialized_)||!owner_||owner_!=token||!lease_||
           observed.index!=actor_.index||observed.serial!=actor_.serial||observed.address!=actor_.address||
           !pool.owns_object(session,lease_,actor_.address)||!entry_source_current(b,visual)||!call_identity(b,actor_))return false;
        if(visual){
#if defined(E33_RUNTIME_CINEMATIC_VERSION) && E33_RUNTIME_CINEMATIC_VERSION>=179
            if(!helper_parameter_anchor_admitted({true,true,visual,arena_staging_,preparing_world_,
                construction_.phase==e33_owned_actor::ConstructionPhase::Complete,helper_battle_quiescent(b)}))return false;
#else
            return false;
#endif
        }else{
            const auto battle=picto_field(b,actor_.address,"IsInBattle","BoolProperty",2930,1);
            if(!battle||local_read<uint8_t>(battle))return false;
        }
        if(exact_name(b,actor_.address+24,"None"))return false;
        name=local_read<uint64_t>(actor_.address+24);return name!=0;
    }
    template<class Pool> bool externally_retired_owned_actor(uint64_t b,uint64_t session,Pool& pool)const{
        const bool exact=actor_.address&&call_identity(b,actor_)==actor_.address;
        bool engine_retired=false;
        if(exact){
            const auto chunks=local_read<uint64_t>(b+0x9361b70);
            const auto slot=local_read<uint64_t>(chunks+uint64_t(actor_.index>>16)*8)+uint64_t(actor_.index&65535)*24;
            engine_retired=(local_read<uint8_t>(actor_.address+0x5d)&1)||
                (local_read<uint32_t>(actor_.address+8)&0x40018000U)||(local_read<uint32_t>(slot+8)&0x200000U);
        }
        return e33_owned_actor::externally_retired(TargetPodSchemaOps{b}.context(),exact,
            exact&&lease_&&pool.owns_object(session,lease_,actor_.address),
            exact&&local_read<uint64_t>(actor_.address+16)==ids_[4].address,
            exact&&call_identity(b,ids_[2])&&arena_world(b,actor_.address,ids_[2].address),
            engine_retired);
    }
    template<class Pool> bool purged_owned_actor(uint64_t b,uint64_t session,Pool& pool)const{
        // Check registry serials before any actor/world dereference. Forced
        // map purge can invalidate actors even while collector storage exists.
        return e33_owned_actor::purged(TargetStrongReferenceOps{b,{-1,0,0}}.can_release(),
            actor_.address&&!call_identity(b,actor_),ids_[2].address&&!call_identity(b,ids_[2]),
            lease_&&pool.owns_retirement_storage(session,lease_,actor_.address));
    }
    template<class Pool> uint32_t close(uint64_t b,uint64_t session,Pool& pool){
        if(trigger_anchor_)return close_trigger(b,session,pool);
        if(!TargetStrongReferenceOps{b,{-1,0,0}}.can_release())return 407;
        if(arena_staging_&&e33_owned_actor::allocation_unresolved(construction_,actor_.address!=0))return 3643;
        const bool already_retired=arena_staging_&&externally_retired_owned_actor(b,session,pool);
        const bool actor_valid=!already_retired&&actor_.address&&call_identity(b,actor_);
        struct HelperRetirementOps{
            Owner& owner;uint64_t base;
            bool context(){return TargetPodSchemaOps{base}.context();}
            bool fresh_battle_quiescent(bool& result){result=owner.helper_battle_quiescent(base);return true;}
        } helper_retirement{*this,b};
        // Direct original-parameter entry does not set a carrier's IsInBattle.
        // Its retained arena therefore needs the same independent entry journal
        // as a visual helper. Ordinary overlap-started enemies are unchanged.
        const auto helper_gate=helper_retirement_gate(helper_retirement,owner_||lease_,
            actor_valid&&(visual_class(b)||helper_entry_.phase()!=HelperEntryPhase::Empty));
        if(helper_gate)return helper_gate;
        struct RetirementOps{
            uint64_t base,actor;
            bool context(){return TargetPodSchemaOps{base}.context();}
            bool battle_state(bool& value){
                const auto field=picto_field(base,actor,"IsInBattle","BoolProperty",2930,1);
                if(!field)return false;
                const auto observed=local_read<uint8_t>(field);
                if(observed>1)return false;
                value=observed!=0;return true;
            }
        } retirement{b,actor_.address};
        const auto gate=enemy_retirement_gate(retirement,owner_||lease_,actor_valid&&!visual_class(b));
        if(gate)return gate; // no destruction or lease release before readiness
        EngineExtraSpots<Pool> extra_ops(b,session,pool,extra_spots_);
        const auto extra_cleanup=extra_spots_.transaction.close(extra_ops);
        if(extra_cleanup!=ExtraSpotsResult::Ok)return extra_cleanup==ExtraSpotsResult::CleanupDeferred?407:2987;
        if(!close_arena_binding_temporary(arena_binding_,arena_binding_state_))return 2957;
        if(!arena_binding_.close_owned_value())return 2957;
        if(actor_valid){
            std::memset(args_,0,sizeof(args_));if(!call(b,2,ids_[7],actor_))return 2907;
            actor_={};
        }
        if(lease_){TargetStrongReferenceOps ops{b,{-1,0,0}};if(pool.release(ops,session,lease_)!=StrongLeaseResult::Ok)return 2908;lease_=0;}
        if(authored_cdo_lease_){TargetStrongReferenceOps ops{b,{-1,0,0}};if(pool.release(ops,session,authored_cdo_lease_)!=StrongLeaseResult::Ok)return 3030;authored_cdo_lease_=0;}
        // Externally retired/stale actors skip DestroyActor above. Their old
        // identity must not survive successful close into a new allocation.
        actor_={};
        authored_cdo_={};
        for(auto& component_target:component_pose_targets_)component_target={};
        arena_ground_attempted_=arena_grounded_=false;arena_ground_journal_={};
        arena_ground_frame_function_={};arena_ground_rotation_function_={};
        for(auto& placement:combat_placements_)placement={};
        owner_=0;attempted_=false;initialized_=false;placement_attempted_=false;arena_binding_state_={};arena_binding_={};extra_spots_={};preparing_world_=false;grounded_=false;movement_={};movement_function_={};helper_entry_={};encounter_override_={};encounter_table_={};construction_={};return 0;
    }
    template<class Pool> void command(uint64_t b,uint64_t session,Pool& pool,MeshPacket& p){
        auto* raw=reinterpret_cast<uint8_t*>(&p);
        if(arena_staging_&&p.operation!=120&&p.operation!=111){p.error=3600;return;}
        if(trigger_anchor_&&p.operation!=120&&p.operation!=111&&p.operation!=118){p.error=3650;return;}
        if(p.version!=3||p.error||p.state||!p.owner||((p.operation<110||p.operation>123)&&p.operation!=131&&p.operation!=132&&p.operation!=133)){p.error=2900;return;}
        if(owner_&&owner_!=p.owner){p.error=2901;return;}
        if(p.operation==111){p.error=close(b,session,pool);return;}
        if(p.operation==131){
            if(!owner_||!lease_||!visual_class(b)||!entry_source_current(b,true)||!call_identity(b,actor_)||
               !pool.owns_object(session,lease_,actor_.address)){p.error=2993;return;}
            CallIdentity query{};std::memcpy(&query,raw+88,sizeof(query));
            std::memset(args_,0,sizeof(args_));put(0,ids_[2].address);put(8,ids_[4].address);
            if(!call(b,102,query,ids_[3])){p.error=2993;return;}
            const auto selected=call_capture(b,local_read<uint64_t>(reinterpret_cast<uint64_t>(args_+16)));
            if(selected.index!=actor_.index||selected.serial!=actor_.serial||selected.address!=actor_.address){p.error=2994;return;}
            std::memcpy(raw+4096,&selected,16);p.state=1;return;
        }
        if(p.operation==123){
            CallIdentity query[7]{};double destination[3]{},result[12]{};
            std::memcpy(query,raw+88,sizeof(query));std::memcpy(destination,raw+2000,sizeof(destination));
            p.error=place_combatant(b,query,destination,result);if(p.error)return;
            std::memcpy(raw+4096,result,sizeof(result));p.state=1;return;
        }
        if(p.operation==122){
            if(!owner_||!initialized_){p.error=2980;return;}
            if(!current(b)){p.error=2988;return;}
            if(!arena_binding_state_.verified){p.error=2989;return;}
            if(extra_spots_.transaction.pending()){p.error=2990;return;}
            CallIdentity query[8]{};std::memcpy(query,raw+88,sizeof(query));
            for(const auto& id:query)if(!call_identity(b,id)){p.error=2991;return;}
            const auto arena=arena_binding_.observed_arena();
            if(query[0].index!=arena.index||query[0].serial!=arena.serial||query[0].address!=arena.address){p.error=2992;return;}
            const auto count=local_read<uint32_t>(reinterpret_cast<uint64_t>(raw+32));
            extra_spots_.world=ids_[2];extra_spots_.actor=actor_;extra_spots_.arena=arena;
            extra_spots_.component_class=query[1];extra_spots_.spot_class=query[2];
            std::memcpy(extra_spots_.functions,query+3,sizeof(extra_spots_.functions));
            EngineExtraSpots<Pool> ops(b,session,pool,extra_spots_);
            const auto result=extra_spots_.transaction.stage(ops,count);
            if(result!=ExtraSpotsResult::Ok){p.error=2980+static_cast<uint32_t>(result);return;}
            const auto mask=(uint64_t(1)<<count)-1;
            std::memcpy(raw+4096,&mask,8);p.state=1;return;
        }
        if(p.operation==121){
            if(!owner_||!preparing_world_||initialized_||placement_attempted_||!current(b)||!call_identity(b,actor_)){p.error=2970;return;}
            CallIdentity query[9]{};std::memcpy(query,raw+88,sizeof(query));
            for(const auto& id:query)if(!call_identity(b,id)){p.error=2970;return;}
            double result[30]{};p.error=place_grounded(b,query,result);if(p.error)return;
            std::memcpy(raw+4096,result,sizeof(result));p.state=1;return;
        }
        if(p.operation==119){
            if(owner_||attempted_||!TargetPodSchemaOps{b}.context()){p.error=2960;return;}
            CallIdentity query[6]{};std::memcpy(query,raw+88,sizeof(query));
            for(const auto& id:query)if(!call_identity(b,id)){p.error=2960;return;}
            if(!arena_class(b,query[0].address,"World","/Script/Engine")||
               !arena_class(b,query[1].address,"PlayerController","/Script/Engine")||
               !arena_class(b,query[2].address,"Pawn","/Script/Engine")||
               !arena_world(b,query[1].address,query[0].address)||!arena_world(b,query[2].address,query[0].address)||
               !named(b,query[4].address,"Default__KismetSystemLibrary","/Script/Engine")){p.error=2960;return;}
            std::memset(args_,0,sizeof(args_));
            if(!call(b,21,query[3],query[1])||local_read<uint64_t>(reinterpret_cast<uint64_t>(args_))!=query[2].address){p.error=2960;return;}
            double probe[6]{};std::memcpy(probe,raw+2000,sizeof(probe));
            const uint64_t ignored[]={query[2].address};
            const auto result=e33_volume_query::sample([&](uint8_t* frame){
                std::memcpy(args_,frame,sizeof(args_));const bool ok=call(b,101,query[5],query[4]);
                std::memcpy(frame,args_,sizeof(args_));return ok;
            },query[0].address,probe,probe+3,ignored,1);
            if(result==e33_volume_query::Result::Invalid||result==e33_volume_query::Result::Rejected){p.error=2961;return;}
            const uint32_t blocked=result==e33_volume_query::Result::Blocked?1:0;
            std::memcpy(raw+4096,&blocked,4);p.state=1;return;
        }
        if(p.operation==118){
            if(!owner_||initialized_||!current(b)||!call_identity(b,actor_)||
               (visual_class(b)&&!preparing_world_)){p.error=2950;return;}
            if(arena_binding_state_.attempted){p.error=2951;return;}
            CallIdentity query[4]{};std::memcpy(query,raw+88,sizeof(query));
            for(const auto& id:query)if(!call_identity(b,id)){p.error=2952;return;}
            if(trigger_anchor_){
                uint64_t name=0;
                if(!trigger_parameter_name(b,session,pool,p.owner,actor_,name)){p.error=3654;return;}
                trigger_arena_pool_=&pool;trigger_arena_session_=session;
                arena_binding_.configure_owned_presentation_value(b,ids_[2].address,actor_,query[0],query[1],query[2],query[3],this,
                    [](void* context,uint64_t base,const CallIdentity& actor,uint64_t world){
                        auto& held=*static_cast<Owner*>(context);uint64_t instance_name=0;
                        return world==held.ids_[2].address&&held.trigger_arena_pool_&&
                            held.trigger_parameter_name(base,held.trigger_arena_session_,*static_cast<Pool*>(held.trigger_arena_pool_),held.owner_,actor,instance_name,true);
                    });
            }
            else if(visual_class(b))arena_binding_.configure_owned_value(b,ids_[2].address,actor_,query[0],query[1],query[2],query[3]);
            else arena_binding_.configure(b,ids_[2].address,actor_,query[0],query[1],query[2],query[3]);
            const auto result=bind_owned_arena(arena_binding_,arena_binding_state_);
            if(result!=ArenaBindingResult::Ok){p.error=2950+static_cast<uint32_t>(result);return;}
            const auto observed=arena_binding_.observed_arena();
            if(!observed.address){p.error=2958;return;}
            std::memcpy(raw+4096,&actor_,16);std::memcpy(raw+4112,&observed,16);p.state=1;return;
        }
        if(p.operation==117){
            // Read-only current-world assembly query. Does not acquire an owner
            // or lease and deliberately does not require the QA map name.
            if(owner_||attempted_||!TargetPodSchemaOps{b}.context()){p.error=2941;return;}
            CallIdentity query[5]{};std::memcpy(query,raw+88,sizeof(query));
            for(const auto& id:query)if(!call_identity(b,id)){p.error=2941;return;}
            if(!arena_class(b,query[0].address,"World","/Script/Engine")||
               !arena_class(b,query[1].address,"PlayerController","/Script/Engine")||
               !arena_class(b,query[2].address,"Pawn","/Script/Engine")||
               !arena_world(b,query[1].address,query[0].address)||!arena_world(b,query[2].address,query[0].address)){
                p.error=2941;return;
            }
            std::memset(args_,0,sizeof(args_));
            if(!call(b,21,query[3],query[1])||local_read<uint64_t>(reinterpret_cast<uint64_t>(args_))!=query[2].address){p.error=2941;return;}
            ArenaAssemblyObservation observation{};
            p.error=observe_arena_assembly(b,query[0].address,query[4].address,observation);
            if(p.error)return;
            std::memcpy(raw+4096,&observation,sizeof(observation));p.state=1;return;
        }
        if(p.operation==116){
            // Read-only local pawn pose, using existing WorldBuilder profiles.
            // No general Rotator codec and no ownership/actor mutation.
            if(owner_||attempted_){p.error=2938;return;}
            std::memcpy(ids_,raw+88,sizeof(ids_));
            if(!current(b,true)){p.error=2939;return;}
            CallIdentity pose_functions[2]{};std::memcpy(pose_functions,raw+280,sizeof(pose_functions));
            double values[6]{};std::memset(args_,0,sizeof(args_));
            if(!call(b,3,pose_functions[0],ids_[1])){p.error=2939;return;}
            std::memcpy(values,args_,24);std::memset(args_,0,sizeof(args_));
            if(!call(b,4,pose_functions[1],ids_[1])){p.error=2939;return;}
            std::memcpy(values+3,args_,24);
            for(double v:values)if(!std::isfinite(v)||std::abs(v)>1.e7){p.error=2940;return;}
            std::memcpy(raw+4096,values,sizeof(values));p.state=1;return;
        }
        if(p.operation==115||p.operation==132){
#ifdef E33_ENEMY_VISUAL_RESEARCH
            if(!owner_||placement_attempted_||!current(b)||!call_identity(b,actor_)||!visual_class(b)){
                p.error=2930;return;
            }
            CallIdentity query[8]{};std::memcpy(query,raw+88,(p.operation==132?8:7)*sizeof(CallIdentity));
            if(!named(b,query[0].address,"Default__KismetSystemLibrary","/Script/Engine")){
                p.error=2931;return;
            }
            // Measure complete assembly, including child actors, with collision
            // filtering off: the preview is deliberately nonblocking.
            std::memset(args_,0,sizeof(args_));args_[56]=1;
            if(!call(b,25,query[3],actor_)){p.error=2931;return;}
            double center[3],extent[3],old[3],rotation[3],pawn[3],pawn_center[3],pawn_extent[3];
            std::memcpy(center,args_+8,24);std::memcpy(extent,args_+32,24);
            if(p.operation==132){
                e33_geometry::BoundsUnion bounds;
                if(!visit_owned_components(b,actor_.address,[&](uint64_t component){
                    // Child actors need explicit recursive coverage; never silently omit them.
                    if(arena_class(b,component,"ChildActorComponent","/Script/Engine"))return false;
                    if(!arena_class(b,component,"StaticMeshComponent","/Script/Engine")&&
                       !arena_class(b,component,"SkinnedMeshComponent","/Script/Engine"))return true;
                    std::memset(args_,0,sizeof(args_));put(0,component);
                    if(!call(b,64,query[7],query[0]))return false;
                    double component_center[3],component_extent[3];
                    std::memcpy(component_center,args_+8,24);std::memcpy(component_extent,args_+32,24);
                    return bounds.add(component_center,component_extent);
                })||!bounds.result(center,extent)){p.error=2932;return;}
            }
            std::memset(args_,0,sizeof(args_));
            if(!call(b,3,query[4],actor_)){p.error=2931;return;}std::memcpy(old,args_,24);
            std::memset(args_,0,sizeof(args_));
            if(!call(b,4,query[5],actor_)){p.error=2931;return;}std::memcpy(rotation,args_,24);
            std::memset(args_,0,sizeof(args_));
            if(!call(b,3,query[4],ids_[1])){p.error=2931;return;}std::memcpy(pawn,args_,24);
            std::memset(args_,0,sizeof(args_));args_[0]=1;args_[56]=1;
            if(!call(b,25,query[3],ids_[1])){p.error=2931;return;}
            std::memcpy(pawn_center,args_+8,24);std::memcpy(pawn_extent,args_+32,24);
            std::memset(args_,0,sizeof(args_));
            if(!call(b,4,query[5],ids_[1])){p.error=2931;return;}
            double facing[3];std::memcpy(facing,args_,24);
            for(int i=0;i<3;++i){
                if(!std::isfinite(center[i])||!std::isfinite(extent[i])||extent[i]<=0||extent[i]>100000.||
                   !std::isfinite(old[i])||!std::isfinite(rotation[i])||!std::isfinite(pawn[i])||
                   !std::isfinite(pawn_center[i])||!std::isfinite(pawn_extent[i])||pawn_extent[i]<0||
                   !std::isfinite(facing[i])){p.error=2932;return;}
            }
            const double radius=std::hypot(extent[0],extent[1]);
            const double distance=radius+std::hypot(pawn_extent[0],pawn_extent[1])+500.;
            if(!std::isfinite(distance)||distance>200000.){p.error=2932;return;}
            const double yaw=facing[1]*3.14159265358979323846/180.;
            double footprint_center[2]{};
            double maximum=-1.e8,minimum=1.e8;const uint64_t ignored[]={actor_.address,ids_[1].address};
            uint32_t ground_error=2933;
            const auto support=e33_enemy_ground::search(pawn_center,yaw,distance,[&](const double* candidate){
            maximum=-1.e8;minimum=1.e8;
            // Ground evidence only: nine samples do not certify obstacle-free
            // volume or every animation phase. Collision remains disabled.
            for(int y=-1;y<=1;++y)for(int x=-1;x<=1;++x){
                const double start[]={candidate[0]+x*extent[0],candidate[1]+y*extent[1],pawn[2]+5000.};
                const double end[]={start[0],start[1],pawn[2]-10000.};
                e33_surface_query::Sample ground{};
                const auto result=e33_surface_query::sample([&](unsigned stage,uint8_t* values){
                    std::memcpy(args_,values,sizeof(args_));
                    const bool ok=stage?call(b,15,query[2],ids_[3]):call(b,14,query[1],query[0]);
                    std::memcpy(values,args_,sizeof(args_));return ok;
                },ids_[2].address,start,end,ignored,2,ground);
                if(result!=e33_surface_query::Result::Hit){
                    ground_error=result==e33_surface_query::Result::Rejected?2931:2933;
                    if(ground_error==2933){
                        double diagnostic[24]={122.,double((y+1)*3+x+1),double(static_cast<unsigned>(result))};
                        std::memcpy(diagnostic+3,start,24);std::memcpy(diagnostic+6,end,24);
                        std::memcpy(diagnostic+9,extent,24);std::memcpy(diagnostic+12,center,24);
                        std::memcpy(diagnostic+15,pawn,24);std::memcpy(diagnostic+18,candidate,16);
                        diagnostic[20]=distance;diagnostic[21]=radius;diagnostic[22]=minimum;diagnostic[23]=maximum;
                        std::memcpy(raw+4096,diagnostic,sizeof(diagnostic));
                    }
                    return result==e33_surface_query::Result::NoHit?e33_enemy_ground::Support::Unsupported:e33_enemy_ground::Support::Rejected;
                }
                maximum=std::max(maximum,ground.point[2]);minimum=std::min(minimum,ground.point[2]);
            }
            if(maximum-minimum>250.){
                ground_error=2934;
                double diagnostic[24]={129.,9.,4.};
                std::memcpy(diagnostic+9,extent,24);std::memcpy(diagnostic+12,center,24);
                std::memcpy(diagnostic+15,pawn,24);std::memcpy(diagnostic+18,candidate,16);
                diagnostic[20]=distance;diagnostic[21]=radius;diagnostic[22]=minimum;diagnostic[23]=maximum;
                std::memcpy(raw+4096,diagnostic,sizeof(diagnostic));
                return e33_enemy_ground::Support::Unsupported;
            }
            return e33_enemy_ground::Support::Accepted;
            },footprint_center);
            if(support!=e33_enemy_ground::Support::Accepted){p.error=ground_error;return;}
            const double destination[]={footprint_center[0]-(center[0]-old[0]),footprint_center[1]-(center[1]-old[1]),
                maximum+100.-(center[2]-extent[2]-old[2])};
            for(double value:destination)if(!std::isfinite(value)||std::abs(value)>1.e8){p.error=2932;return;}
            placement_attempted_=true; // no replay after uncertain mutation
            std::memset(args_,0,sizeof(args_));std::memcpy(args_,destination,24);std::memcpy(args_+24,rotation,24);args_[304]=1;
            if(!call(b,5,query[6],actor_)||!args_[305]){p.error=2935;return;}
            // Prepared original Actor helpers have no CharacterMovement.
            // Resume their authored actor tick only after bounded placement;
            // keep collision disabled throughout this assembly-only stage.
            if(preparing_world_){
                std::memset(args_,0,sizeof(args_));args_[0]=1;
                if(!call(b,58,ids_[10],actor_)){p.error=2936;return;}
            }
            std::memset(args_,0,sizeof(args_));
            if(!call(b,100,ids_[11],actor_)){p.error=2936;return;}
            grounded_=true;
            double result[24]{};std::memcpy(result,destination,24);std::memcpy(result+3,old,24);
            std::memcpy(result+6,center,24);std::memcpy(result+9,extent,24);std::memcpy(result+12,pawn,24);
            std::memcpy(result+15,pawn_extent,24);result[18]=maximum;result[19]=minimum;result[20]=radius;
            result[21]=distance;result[22]=center[2]-extent[2];result[23]=9;
            std::memcpy(raw+4096,result,sizeof(result));p.state=1;return;
#else
            p.error=2930;return;
#endif
        }
        if(p.operation==114){
#ifdef E33_ENEMY_VISUAL_RESEARCH
            if(!owner_||!current(b)||!call_identity(b,actor_)){p.error=2920;return;}
            bool visual=false;
            for(const auto& row:enemy_visual_recipes)if(named(b,ids_[4].address,row[0],row[1])){visual=true;break;}
            CallIdentity identity{};std::memcpy(&identity,raw+88,16);
            const auto body=call_identity(b,identity),a=actor_.address;
            const auto owned_body=picto_field(b,a,"Body","ObjectProperty",664,8);
            uint64_t descriptor=0;
            const auto tick=body?picto_field(b,body,"VisibilityBasedAnimTickOption","EnumProperty",1948,1,&descriptor):0;
            if(!visual||!body||!owned_body||local_read<uint64_t>(owned_body)!=body||
               local_read<uint64_t>(body+32)!=a||!tick||!descriptor||
               local_read<uint64_t>(descriptor)!=b+0x6deeee8||local_read<uint64_t>(descriptor+0x38)!=0x18041240004205ULL||
               !named(b,local_read<uint64_t>(descriptor+0x10)&~uint64_t(1),"SkinnedMeshComponent","/Script/Engine")||
               !named(b,local_read<uint64_t>(descriptor+0x78),"EVisibilityBasedAnimTickOption","/Script/Engine")){
                p.error=2921;return;
            }
            const uint32_t before=local_read<uint8_t>(tick);
            if(before>4){p.error=2922;return;}
            // This invisible rig drives visible socket-attached body parts.
            // The exact policy/profile is already used by the SDK skin owner.
            // Change only this disposable owned component; no CDO or game pause.
            const uint8_t always_tick_pose_and_refresh_bones=0;
            std::memcpy(reinterpret_cast<void*>(tick),&always_tick_pose_and_refresh_bones,1);
            std::memcpy(raw+4096,&before,4);p.state=1;return;
#else
            p.error=2920;return;
#endif
        }
        if(p.operation==113){
            if(helper_entry_.phase()!=HelperEntryPhase::Empty){p.error=2918;return;}
            if(!initialized_||!current(b)||!call_identity(b,actor_)){p.error=2918;return;}
            if(!verify_authored_encounter(b)){p.error=3012;return;}
            CallIdentity function{};std::memcpy(&function,raw+88,16);const auto fn=call_identity(b,function);
            const auto battle=picto_field(b,actor_.address,"IsInBattle","BoolProperty",2930,1);
            if(!fn||!battle||local_read<uint8_t>(battle)||
               !named(b,local_read<uint64_t>(fn+32),"BP_jRPG_Enemy_World_Base_Seamless_C","/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_Enemy_World_Base_Seamless")||
               !exact_name(b,fn+24,"ResetState")||local_read<uint32_t>(fn+0xb0)!=201457664||
               local_read<uint16_t>(fn+0xb6)!=0||local_read<uint16_t>(fn+0xb8)!=65535||local_read<int32_t>(fn+0x58)!=0||
               local_read<uint64_t>(fn+0xd8)!=b+0x13937a0||!fields(b,fn,nullptr,0)){p.error=2919;return;}
            const auto pe=local_read<uint64_t>(local_read<uint64_t>(actor_.address)+0x268);
            if(pe!=b+0x1393330&&pe!=b+0x332bb90){p.error=2917;return;}
            if(preparing_world_&&!release_prepared(b)){p.error=2976;return;}
            std::memset(args_,0,sizeof(args_));
            reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(pe)(reinterpret_cast<void*>(actor_.address),reinterpret_cast<void*>(fn),args_);
            if(!verify_authored_encounter(b)){
                hold_prepared(b);hide_prepared(b);p.error=3012;return;
            }
            p.state=1;return;
        }
        if(p.operation==112){
            if(encounter_override_.pending()&&encounter_override_.phase()!=EncounterOverridePhase::Verified){p.error=3012;return;}
            if(preparing_world_&&(!grounded_||!arena_binding_state_.verified)){p.error=2976;return;}
            if(!owner_||initialized_||!current(b)||!call_identity(b,actor_)){p.error=2914;return;}
            CallIdentity component{},function{};std::memcpy(&component,raw+88,16);std::memcpy(&function,raw+104,16);
            const auto comp=call_identity(b,component),fn=call_identity(b,function),a=actor_.address;
            const auto policy=local_read<uint32_t>(reinterpret_cast<uint64_t>(raw+32));
            // Original campaign instance actions are not yet traced for this
            // route. An explicit candidate must not silently claim fidelity.
            if(encounter_override_.pending()&&policy!=0){p.error=3013;return;}
            if(policy>1||!comp||!fn||local_read<uint64_t>(comp+32)!=a||
               !picto_class(b,comp,"BP_Enemy_SerializableComponent_C","/Game/jRPGTemplate/Blueprints/Basics/BP_Enemy_SerializableComponent")||
               !named(b,local_read<uint64_t>(fn+32),"BP_jRPG_Enemy_World_Base_Seamless_C","/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_Enemy_World_Base_Seamless")||
               !exact_name(b,fn+24,"OnEnemyBattleStateLoaded")||local_read<uint32_t>(fn+0xb0)!=201457664||
               local_read<uint16_t>(fn+0xb6)!=1||local_read<uint16_t>(fn+0xb8)!=65535||local_read<int32_t>(fn+0x58)!=1||
               local_read<uint64_t>(fn+0xd8)!=b+0x13937a0){p.error=2915;return;}
            static const MeshField init_fields[]={{"BattleState","BoolProperty",0,1,2251869606904468ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
            if(!fields(b,fn,init_fields,1)){p.error=2915;return;}
            const auto id=picto_field(b,comp,"GlobalObjectID","NameProperty",160,8);
            const auto action=picto_field(b,a,"GameActionPostBattle","ObjectProperty",2088,8);
            const auto battle=picto_field(b,a,"IsInBattle","BoolProperty",2930,1);
            if(!id||!action||!battle||local_read<uint8_t>(battle)||!exact_name(b,id,"None")||
               !call_derives(b,ids_[4].address,local_read<uint64_t>(fn+32))){p.error=2916;return;}
            const auto pe=local_read<uint64_t>(local_read<uint64_t>(a)+0x268);
            if(pe!=b+0x1393330&&pe!=b+0x332bb90){p.error=2917;return;}
            // FName is a POD engine name; copying the owned actor's unique name
            // avoids creating a codec or borrowing any authored enemy's history ID.
            initialized_=true;
            std::memcpy(reinterpret_cast<void*>(id),reinterpret_cast<void*>(a+24),8);
            // Null only this disposable instance's authored post-battle action.
            // Original mode retains the untouched Blueprint-authored reference.
            if(policy==0){const uint64_t empty=0;std::memcpy(reinterpret_cast<void*>(action),&empty,8);}
            std::memset(args_,0,sizeof(args_));
            reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(pe)(reinterpret_cast<void*>(a),reinterpret_cast<void*>(fn),args_);
            if(preparing_world_&&(!hold_prepared(b)||!hide_prepared(b))){p.error=2976;return;}
            if(!verify_authored_encounter(b)){p.error=3012;return;}
            std::memcpy(raw+4096,&actor_,16);p.state=1;return;
        }
        if(attempted_){p.error=2902;return;}
        std::memcpy(ids_,raw+88,sizeof(ids_));
        if(e33_trigger_anchor::exact_class(b,ids_[4].address)){
            if(arena_staging_||p.operation!=120){p.error=3650;return;}
            trigger_anchor_=true;
            std::memcpy(&trigger_refresh_,raw+280,16);
            if(!call_identity(b,trigger_refresh_)||!e33_trigger_anchor::shipping_assert_safe(b)){p.error=3651;return;}
        }
        if(!current(b,p.operation==120||p.operation==133)){p.error=2903;return;}
        double pose[12]{};std::memcpy(pose,raw+2000,96);
        double norm=0;for(int i=0;i<4;++i)norm+=pose[i]*pose[i];
        for(double v:pose)if(!std::isfinite(v)||std::abs(v)>1.e7){p.error=2904;return;}
        if(norm<.999||norm>1.001||pose[7]!=0||pose[11]!=0||pose[8]!=1||pose[9]!=1||pose[10]!=1){p.error=2904;return;}
        preparing_world_=p.operation==120||p.operation==133;
        if(p.operation==133&&(visual_class(b)||!authored_route(local_read<uint32_t>(reinterpret_cast<uint64_t>(raw+32))))){
            p.error=3010;return;
        }
        if(preparing_world_){
            if(!visual_class(b)&&!trigger_anchor_){
                std::memcpy(&movement_function_,raw+280,16);
                if(!call_identity(b,movement_function_)){p.error=2970;return;}
            }
        }
        attempted_=true;owner_=p.owner;
        if(trigger_anchor_&&!trigger_begin(b,session,pool)){p.error=3652;return;}
        if(p.operation==133){
            std::memcpy(&authored_cdo_,raw+312,16);
            const auto spec=authored_route(local_read<uint32_t>(reinterpret_cast<uint64_t>(raw+32)));
            if(!spec||!call_identity(b,authored_cdo_)||
               local_read<uint64_t>(authored_cdo_.address+16)!=ids_[4].address||
               !(local_read<uint32_t>(authored_cdo_.address+8)&0x10)||
               !named(b,authored_cdo_.address,spec->cdo_name,spec->package)){p.error=3025;return;}
            // Retain and stabilize the exact observed CDO before deferred
            // construction can assign its first weak serial. Zero remains an
            // exact observation, never a wildcard. Release with this owner.
            TargetStrongReferenceOps ops{b,authored_cdo_};
            if(pool.acquire(ops,session,authored_cdo_.address,authored_cdo_lease_)!=StrongLeaseResult::Ok||
               !stabilize_retained_identity(ops,authored_cdo_)){p.error=3030;return;}
        }
        bool preparing_visual=false;
        const auto constructed=e33_owned_actor::construct(construction_,[&](){
        std::memset(args_,0,sizeof(args_));put(0,ids_[2].address);put(8,ids_[4].address);std::memcpy(args_+16,pose,96);args_[112]=1;
        if(!call(b,0,ids_[5],ids_[3])){p.error=2905;return false;}
        return true;
        },[&](){
        actor_=call_capture(b,local_read<uint64_t>(reinterpret_cast<uint64_t>(args_+136)));
        if(!actor_.address){p.error=2906;return false;}
        return true;
        },[&](){
        TargetStrongReferenceOps ops{b,actor_};
        if(trigger_anchor_)trigger_actor_retention_pending_=true;
        if(pool.acquire(ops,session,actor_.address,lease_)!=StrongLeaseResult::Ok || !stabilize_retained_identity(ops,actor_)){p.error=2908;return false;}
        trigger_actor_retention_pending_=false;
        return true;
        },[&](){
        // Visual assemblies are preparation-only until measured placement is
        // available. Disable collision before construction, then reassert it
        // after construction in case the authored script changes the flag.
        preparing_visual=visual_class(b);
        if(preparing_world_&&!hide_prepared(b)){p.error=2970;return false;}
        if(trigger_anchor_&&!e33_trigger_anchor::defaults(b,actor_.address)){p.error=3651;return false;}
        if(p.operation==133){
            CallIdentity table{};std::memcpy(&table,raw+296,16);
            // The private array exists after deferred allocation but before the
            // original construction/BeginPlay chooses SelectedEncounter.
            if(!pool.owns_object(session,lease_,actor_.address)){p.error=3011;return false;}
            uint32_t failure=3011;
            if(!apply_authored_encounter(b,table,authored_cdo_,local_read<uint32_t>(reinterpret_cast<uint64_t>(raw+32)),failure)){
                p.error=failure;return false;
            }
        }
        if(preparing_visual){
            std::memset(args_,0,sizeof(args_));
            if(!call(b,47,ids_[9],actor_)){p.error=2911;return false;}
        }
        return true;
        },[&](){
        std::memset(args_,0,sizeof(args_));put(0,actor_.address);std::memcpy(args_+16,pose,96);
        if(!call(b,1,ids_[6],ids_[3])||local_read<uint64_t>(reinterpret_cast<uint64_t>(args_+120))!=actor_.address){p.error=2909;return false;}
        return true;
        },[&](){
        if(preparing_world_){
            if(trigger_anchor_){
                if(!trigger_finalize(b,session,pool)){p.error=3654;return false;}
                return true;
            }
            if((!preparing_visual&&!hold_prepared(b))||!hide_prepared(b)){p.error=2970;return false;}
            if(arena_staging_){
                // Only this disposable instance is affected. Do this in the
                // same game-thread transaction, before a streaming update.
                const auto source=arena_reference(b,actor_.address,"WorldPartitionStreamingSource",672);
                uint64_t descriptor=0;
                const auto flag=source?picto_field(b,source,"bStreamingSourceEnabled","BoolProperty",249,1,&descriptor):0;
                if(!source||local_read<uint64_t>(source+32)!=actor_.address||
                   !arena_class(b,source,"WorldPartitionStreamingSourceComponent","/Script/Engine")||
                   !flag||!descriptor||local_read<uint32_t>(descriptor+0x70)!=0xff010001U||
                   local_read<uint8_t>(flag)>1||!pool.owns_object(session,lease_,actor_.address)){
                    p.error=3603;return false;
                }
                const uint8_t disabled=0;
                std::memcpy(reinterpret_cast<void*>(flag),&disabled,1);
                if(local_read<uint8_t>(flag)){p.error=3603;return false;}
            }
            if(!verify_authored_encounter(b)){p.error=3012;return false;}
            return true;
        }
        // The cooked world CDO starts hidden with actor collision disabled.
        // Enable only this owned instance immediately, before it falls through
        // the floor while Python reads assembly metadata. No AI/history edits.
        std::memset(args_,0,sizeof(args_));args_[0]=preparing_visual?0:1;
        if(!call(b,47,ids_[9],actor_)){p.error=2911;return false;}
        std::memset(args_,0,sizeof(args_));args_[0]=1;
        if(!call(b,58,ids_[10],actor_)){p.error=2912;return false;}
        std::memset(args_,0,sizeof(args_));args_[0]=preparing_visual?1:0;
        if(!call(b,100,ids_[11],actor_)){p.error=2913;return false;}
        return true;
        });
        if(constructed!=e33_owned_actor::ConstructionResult::Complete){
            if(!p.error)p.error=2902;
            return;
        }
        if(arena_staging_){
            ArenaAssemblyObservation observation{};
            p.error=observe_arena_assembly(b,ids_[2].address,actor_.address,observation);
            if(p.error)return;
            if(observation.streaming_enabled){p.error=3603;return;}
        }
        std::memcpy(raw+4096,&actor_,16);p.state=1;
    }
};
}
#pragma warning(pop)
