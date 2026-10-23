#pragma once
#include "npc_presentation_admission.h"
#include "npc_presentation_lifecycle.h"
#include "validated_engine_profile_call.h"
#include "actor_visibility_profile.h"
#include "engine_profiles.h"
#include "stable_identity.h"
#include "target_strong_reference.h"
#include "picto_progression.h"
#include <cmath>

// Actual fixed engine callbacks for Lifecycle::stage. No packet or spawn menu
// exposes this bridge until its owning service supplies the remaining measured
// assembly/listener/EndPlay gates and connects original unregister retirement.
namespace e33_npc_presentation {
struct ConstructionSource {
    CallIdentity controller,world,gameplay_statics,actor_class,cdo,available;
    CallIdentity begin,finish,destroy,collision,tick,hidden,movement;
    uint64_t session=0,class_lease=0,cdo_lease=0;
    double transform[12]{};
};
#pragma warning(push)
#pragma warning(disable:4324)
struct ConstructionState {
    CallIdentity actor{},movement{};
    uint64_t actor_lease=0,returned_address=0;
    uint8_t original_movement_mode=0,original_custom_mode=0;
    uint32_t original_guid[4]{};
    alignas(16) uint8_t arguments[144]{};
};
#pragma warning(pop)

template<class Pool,class Guard> struct OriginalConstructionOps {
    uint64_t base;ConstructionSource& source;ConstructionState& state;Pool& pool;Guard& guard;
    bool current_context(){
        const auto b=base;const auto& s=source;
        if(!TargetPodSchemaOps{b}.context()||!guard.current_context()||
           !call_identity(b,s.controller)||!call_identity(b,s.world)||
           !e33_mesh::named(b,local_read<uint64_t>(s.world.address+16),"World","/Script/Engine")||
           !call_identity(b,s.gameplay_statics)||
           !e33_mesh::named(b,s.gameplay_statics.address,"Default__GameplayStatics","/Script/Engine"))return false;
        auto outer=s.controller.address;unsigned walked=0;
        for(;outer&&outer!=s.world.address&&++walked<32;outer=local_read<uint64_t>(outer+32)){}
        return outer==s.world.address;
    }
    bool battle_quiescent(){return guard.battle_quiescent();}
    bool exact_original_admission(){
        const auto& s=source;
        if(!s.session||!s.class_lease||!s.cdo_lease||s.actor_class.serial<=0||s.cdo.serial<=0||
           !pool.owns_object(s.session,s.class_lease,s.actor_class.address)||
           !pool.owns_object(s.session,s.cdo_lease,s.cdo.address)||
           !presentation_class_contract(base,s.actor_class,s.cdo,s.available))return false;
        double norm=0;
        for(unsigned i=0;i<12;++i){
            const auto value=s.transform[i];
            if(!std::isfinite(value)||std::abs(value)>1.e7)return false;
            if(i<4)norm+=value*value;
        }
        // Preserve original actor scale. Component transforms remain entirely
        // under original Blueprint construction; this is not mesh fitting.
        return norm>=.999&&norm<=1.001&&s.transform[7]==0&&s.transform[11]==0&&
            s.transform[8]==1&&s.transform[9]==1&&s.transform[10]==1;
    }
    template<class T> void put(size_t at,const T& value){std::memcpy(state.arguments+at,&value,sizeof(value));}
    bool engine(const CallIdentity& function,const CallIdentity& recipient,const MeshFunction& profile){
        return current_context()&&battle_quiescent()&&
            e33_engine_profile_call::invoke(base,function,recipient,profile,state.arguments);
    }
    bool exact_owned_actor(){
        if(!current_context()||!call_identity(base,state.actor)||
           !pool.owns_object(source.session,state.actor_lease,state.actor.address)||
           local_read<uint64_t>(state.actor.address+16)!=source.actor_class.address||
           (local_read<uint32_t>(state.actor.address+8)&0x30))return false;
        auto outer=state.actor.address;unsigned walked=0;
        for(;outer&&outer!=source.world.address&&++walked<32;outer=local_read<uint64_t>(outer+32)){}
        return outer==source.world.address;
    }
    bool allocate_once(){
        if(!current_context()||!battle_quiescent()||!exact_original_admission())return false;
        std::memset(state.arguments,0,sizeof(state.arguments));
        put(0,source.world.address);put(8,source.actor_class.address);
        std::memcpy(state.arguments+16,source.transform,96);state.arguments[112]=1;
        if(!engine(source.begin,source.gameplay_statics,e33_engine_profiles::profiles[0]))return false;
        std::memcpy(&state.returned_address,state.arguments+136,8);
        return true;
    }
    bool record_returned_actor(){
        // Record before a further engine call or fallible strong retention.
        state.actor=call_capture(base,state.returned_address);
        return state.actor.address!=0;
    }
    bool retain_and_stabilize(){
        if(!current_context()||!battle_quiescent()||!call_identity(base,state.actor)||
           local_read<uint64_t>(state.actor.address+16)!=source.actor_class.address)return false;
        TargetStrongReferenceOps ops{base,state.actor};
        return pool.acquire(ops,source.session,state.actor.address,state.actor_lease)==StrongLeaseResult::Ok&&
            stabilize_retained_identity(ops,state.actor);
    }
    bool hold_private(){
        if(!exact_owned_actor()||!exact_original_admission())return false;
        std::memset(state.arguments,0,sizeof(state.arguments));
        if(!engine(source.collision,state.actor,e33_engine_profiles::profiles[47]))return false;
        std::memset(state.arguments,0,sizeof(state.arguments));
        if(!engine(source.tick,state.actor,e33_engine_profiles::profiles[58]))return false;
        std::memset(state.arguments,0,sizeof(state.arguments));state.arguments[0]=1;
        if(!engine(source.hidden,state.actor,e33_actor_visibility::hidden))return false;
        const auto at=picto_field(base,state.actor.address,"CharacterMovement","ObjectProperty",800,8);
        const auto movement=at?local_read<uint64_t>(at):0;
        if(!movement||local_read<uint64_t>(movement+32)!=state.actor.address||
           !e33_mesh::named(base,local_read<uint64_t>(movement+16),"CharacterMovementComponent","/Script/Engine"))return false;
        const auto mode=picto_field(base,movement,"MovementMode","ByteProperty",513,1);
        const auto custom=picto_field(base,movement,"CustomMovementMode","ByteProperty",514,1);
        if(!mode||!custom||local_read<uint8_t>(mode)>6)return false;
        if(!state.movement.address){
            state.movement=call_capture(base,movement);
            state.original_movement_mode=local_read<uint8_t>(mode);
            state.original_custom_mode=local_read<uint8_t>(custom);
        }else if(call_identity(base,state.movement)!=movement)return false;
        std::memset(state.arguments,0,sizeof(state.arguments));
        return engine(source.movement,state.movement,e33_engine_profiles::profiles[10]);
    }
    bool prepare_private_instance(){return hold_private();}
    bool finish_original_construction(){
        if(!exact_owned_actor()||!exact_original_admission())return false;
        std::memset(state.arguments,0,sizeof(state.arguments));put(0,state.actor.address);
        std::memcpy(state.arguments+16,source.transform,96);
        if(!engine(source.finish,source.gameplay_statics,e33_engine_profiles::profiles[1]))return false;
        uint64_t returned=0;std::memcpy(&returned,state.arguments+120,8);
        return returned==state.actor.address&&exact_owned_actor();
    }
    bool verify_original_identity_assembly_and_hold(){
        if(!hold_private())return false;
        uint64_t descriptor=0;
        const auto id=picto_field(base,state.actor.address,"NPC_ID","StructProperty",1792,16,&descriptor);
        const auto defaults=picto_field(base,source.cdo.address,"NPC_ID","StructProperty",1792,16);
        if(!id||!defaults||!descriptor||
           !e33_mesh::named(base,local_read<uint64_t>(descriptor+0x70),"Guid","/Script/CoreUObject"))return false;
        uint32_t any=0;
        for(unsigned i=0;i<4;++i){
            if(local_read<uint32_t>(defaults+uint64_t(i)*4))return false;
            state.original_guid[i]=local_read<uint32_t>(id+uint64_t(i)*4);any|=state.original_guid[i];
        }
        // Original construction, never a manual GUID write. Cross-instance
        // uniqueness and full body/face/hair/accessory inspection remain the
        // owning service's explicit measured gate.
        return any&&guard.verify_original_assembly_and_identity(state.actor,state.original_guid);
    }
    bool destroy_owned_actor_once(){
        if(!exact_owned_actor()||!battle_quiescent())return false;
        std::memset(state.arguments,0,sizeof(state.arguments));
        return engine(source.destroy,state.actor,e33_engine_profiles::profiles[2]);
    }
};
}
