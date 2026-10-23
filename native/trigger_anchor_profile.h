#pragma once
// Exact original trigger profile only. The caller owns context/world, leases,
// single-attempt dispatch journaling, hidden placement, and retirement authority.
#ifndef E33_TRIGGER_ANCHOR_PROFILE_FIXTURE
#include "mesh_owner.h"
#include "picto_progression.h"
#include "npc_listener_observation.h"
#endif
#include <cstddef>
#include <cstdint>
#include <cstring>

namespace e33_trigger_anchor {
inline constexpr const char* package="/Game/LevelTools/MovementZone/BP_GameActionTriggerZone";
inline constexpr const char* class_name="BP_GameActionTriggerZone_C";
inline constexpr const char* interaction_package="/Game/Gameplay/Exploration/Interaction/BP_Interaction_SerializableComponent";
inline constexpr const char* serializable_package="/Game/Blueprints/Tools/Serializable/BP_SerializableActorComponent";
inline constexpr const char* condition_package="/Game/Gameplay/ConditionChecker/BP_ConditionCheckerComponent";
#include "trigger_anchor_profiles.inl"

inline bool shipping_assert_safe(uint64_t base) {
    if(!TargetPodSchemaOps{base}.context())return false;
    // All 300 bytes through RET. Following INT3 alignment bytes are irrelevant.
    for(size_t i=0;i<sizeof(shipping_assert_bytes);++i)
        if(local_read<uint8_t>(base+0x4abcfd0+i)!=shipping_assert_bytes[i])return false;
    return true;
}

inline bool exact_class(uint64_t base,uint64_t cls) {
    if(!TargetPodSchemaOps{base}.context()||!call_is_class(base,cls)||
       !e33_mesh::named(base,cls,class_name,package)||local_read<int32_t>(cls+0x58)!=816)return false;
    const auto parent=local_read<uint64_t>(cls+0x40);
    return call_is_class(base,parent)&&e33_mesh::named(base,parent,"Actor","/Script/Engine")&&
        local_read<int32_t>(parent+0x58)==656&&shipping_assert_safe(base);
}

inline uint64_t exact_field(uint64_t base,uint64_t object,const char* name,const char* type,
        int offset,int width,uint64_t table,uint64_t flags,const char* owner,const char* owner_package,
        uint64_t* descriptor=nullptr) {
    uint64_t field=0;
    const auto at=picto_field(base,object,name,type,offset,width,&field);
    if(!at||!field||local_read<uint64_t>(field)!=base+table||
       local_read<uint64_t>(field+0x38)!=flags||
       !e33_mesh::named(base,local_read<uint64_t>(field+16)&~uint64_t(1),owner,owner_package))return 0;
    if(descriptor)*descriptor=field;
    return at;
}

inline uint64_t component_slot(uint64_t base,uint64_t actor,const char* name,int offset,
        const char* constraint,const char* constraint_package) {
    uint64_t field=0;
    const auto at=exact_field(base,actor,name,"ObjectProperty",offset,8,0x6e11d38,
        0x8001400080204ULL,class_name,package,&field);
    const auto constraint_class=field?local_read<uint64_t>(field+0x70):0;
    return at&&call_is_class(base,constraint_class)&&e33_mesh::named(base,constraint_class,constraint,constraint_package)?at:0;
}

inline bool empty_wrapper(uint64_t base,uint64_t actor,const char* name,int offset) {
    uint64_t descriptor=0;
    const auto at=exact_field(base,actor,name,"StructProperty",offset,16,0x6e136a0,
        0x9040000205ULL,class_name,package,&descriptor);
    const auto wrapper=descriptor?local_read<uint64_t>(descriptor+0x70):0;
    if(!at||!e33_mesh::named(base,wrapper,"GameAction_Wrapper","/Script/SandFall")||
       local_read<int32_t>(wrapper+0x58)!=16||!e33_mesh::fields(base,wrapper,wrapper_fields,2))return false;
    auto field=local_read<uint64_t>(wrapper+0x50);
    for(unsigned i=0;i<2;++i,field=local_read<uint64_t>(field+24)){
        const auto constraint_class=local_read<uint64_t>(field+0x70);
        if(!call_is_class(base,constraint_class)||!e33_mesh::named(base,constraint_class,"GameAction","/Script/SandFall"))return false;
    }
    return !local_read<uint64_t>(at)&&!local_read<uint64_t>(at+8);
}

inline bool actor_bool(uint64_t base,uint64_t actor,const char* name,int offset,bool require_false) {
    uint64_t field=0;
    const auto at=exact_field(base,actor,name,"BoolProperty",offset,1,0x6e119b0,
        0x8001040010205ULL,class_name,package,&field);
    return at&&local_read<uint32_t>(field+0x70)==0xff010001U&&
        local_read<uint8_t>(at)<=1&&(!require_false||!local_read<uint8_t>(at));
}

inline uint64_t serializable_field(uint64_t base,uint64_t component,uint64_t actor) {
    if(!TargetPodSchemaOps{base}.context()||!call_capture(base,actor).address||!call_capture(base,component).address||
       (local_read<uint32_t>(actor+8)&0x40018030U)||(local_read<uint32_t>(component+8)&0x40018030U)||
       !exact_class(base,local_read<uint64_t>(actor+16))||local_read<uint64_t>(component+32)!=actor)return 0;
    const auto slot=component_slot(base,actor,"BP_Interaction_SerializableComponent",688,
        "BP_Interaction_SerializableComponent_C",interaction_package);
    if(!slot||local_read<uint64_t>(slot)!=component)return 0;
    const auto cls=local_read<uint64_t>(component+16),parent=local_read<uint64_t>(cls+0x40);
    if(!call_is_class(base,cls)||!e33_mesh::named(base,cls,"BP_Interaction_SerializableComponent_C",interaction_package)||
       local_read<int32_t>(cls+0x58)!=185||!call_is_class(base,parent)||
       !e33_mesh::named(base,parent,"BP_SerializableActorComponent_C",serializable_package)||
       local_read<int32_t>(parent+0x58)!=176)return 0;
    uint64_t transient_descriptor=0;
    const auto transient=exact_field(base,component,"IsTransient","BoolProperty",184,1,0x6e119b0,
        0x8001040000205ULL,"BP_Interaction_SerializableComponent_C",interaction_package,&transient_descriptor);
    if(!transient||local_read<uint32_t>(transient_descriptor+0x70)!=0xff010001U||local_read<uint8_t>(transient))return 0;
    return exact_field(base,component,"GlobalObjectID","NameProperty",160,8,0x6e13040,
        0x8041040000205ULL,"BP_SerializableActorComponent_C",serializable_package);
}

inline bool empty_profile(uint64_t base,uint64_t object,bool require_initial_state,bool allow_cdo) {
    if(!TargetPodSchemaOps{base}.context()||!call_capture(base,object).address||!exact_class(base,local_read<uint64_t>(object+16))||
       (local_read<uint32_t>(object+8)&0x40018020U))return false;
    const bool cdo=(local_read<uint32_t>(object+8)&0x10U)!=0;
    if(cdo&&(!allow_cdo||!e33_mesh::named(base,object,"Default__BP_GameActionTriggerZone_C",package)))return false;
    uint64_t reset_descriptor=0;
    const auto reset=exact_field(base,object,"ResetCategory","ByteProperty",713,1,0x6e10420,
        0x8001040000205ULL,class_name,package,&reset_descriptor);
    const auto reset_enum=reset_descriptor?local_read<uint64_t>(reset_descriptor+0x70):0;
    if(!reset||!call_capture(base,reset_enum).address||!exact_name(base,reset_enum+24,"E_GameActionTriggerZoneResetCategory")||
       local_read<uint8_t>(reset)||!actor_bool(base,object,"IsBehaviorDone",714,require_initial_state)||
       !actor_bool(base,object,"IsGameActionOnOverlapPlaying",752,true)||
       !actor_bool(base,object,"IsGameActionOnInteractPlaying",776,true)||
       !empty_wrapper(base,object,"GameActionOnOverlap",736)||
       !empty_wrapper(base,object,"GameActionOnInteract",760))return false;
    const auto cs=component_slot(base,object,"BP_ConditionCheckerComponent",672,"BP_ConditionCheckerComponent_C",condition_package);
    const auto ss=component_slot(base,object,"BP_Interaction_SerializableComponent",688,"BP_Interaction_SerializableComponent_C",interaction_package);
    if(!cs||!ss)return false;
    const auto condition=local_read<uint64_t>(cs),serializable=local_read<uint64_t>(ss);
    // CDO and allocated pre-SCS instances legitimately have a null pair.
    if(!condition&&!serializable)return true;
    if(cdo||!condition||!serializable||local_read<uint64_t>(condition+32)!=object||
       (local_read<uint32_t>(condition+8)&0x40018030U))return false;
    return e33_npc_presentation::empty_condition_wrapper(base,call_capture(base,condition))&&
        serializable_field(base,serializable,object)!=0;
}

// Initial allocation/CDO preflight: every original behavior/playing flag is false.
inline bool defaults(uint64_t base,uint64_t object) {
    return empty_profile(base,object,true,true);
}

// Runtime refresh/retirement invariant. BeginPlay may have observed a preexisting
// None-key state; this never authorizes executing a wrapper or resetting campaign state.
// A null component pair permits cleanup of a failed pre-SCS allocation.
inline bool safe_empty_instance(uint64_t base,uint64_t object) {
    return empty_profile(base,object,false,false);
}

inline bool refresh_preflight(uint64_t base,const CallIdentity& function,const CallIdentity& actor) {
    const auto fn=call_identity(base,function),a=call_identity(base,actor);
    if(!TargetPodSchemaOps{base}.context()||!fn||!a||(local_read<uint32_t>(a+8)&0x40018030U)||
       !safe_empty_instance(base,a)||!e33_mesh::named(base,local_read<uint64_t>(fn+16),"Function","/Script/CoreUObject")||
       local_read<uint64_t>(fn+32)!=local_read<uint64_t>(a+16)||
       !exact_name(base,fn+24,"UpdateTriggerComponentsCollision")||
       local_read<uint32_t>(fn+0xb0)!=0x0c840000U||local_read<uint16_t>(fn+0xb6)!=0||
       local_read<uint16_t>(fn+0xb8)!=65535||local_read<int32_t>(fn+0x58)!=51||
       local_read<uint64_t>(fn+0xd8)!=base+0x13937a0||
       !e33_mesh::fields(base,fn,refresh_local_fields,11))return false;
    // These 11 FProperties describe Blueprint locals, not caller arguments.
    // Reject any CPF_Parm bit even if ParmsSize has been left at zero.
    auto field=local_read<uint64_t>(fn+0x50);unsigned count=0;
    for(;field&&count<32;field=local_read<uint64_t>(field+24),++count)
        if(local_read<uint64_t>(field+0x38)&0x80ULL)return false;
    if(field||count!=11)return false;
    const auto slot=component_slot(base,a,"BP_Interaction_SerializableComponent",688,
        "BP_Interaction_SerializableComponent_C",interaction_package);
    const auto id=slot?serializable_field(base,local_read<uint64_t>(slot),a):0;
    if(!id||exact_name(base,id,"None"))return false;
    const auto pe=local_read<uint64_t>(local_read<uint64_t>(a)+0x268);
    return pe==base+0x1393330||pe==base+0x332bb90;
}

inline bool invoke_refresh(uint64_t base,const CallIdentity& function,const CallIdentity& actor) {
    if(!refresh_preflight(base,function,actor))return false;
    const auto pe=local_read<uint64_t>(local_read<uint64_t>(actor.address)+0x268);
    alignas(16) uint8_t no_arguments[1]{};
    reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(pe)(reinterpret_cast<void*>(actor.address),
        reinterpret_cast<void*>(function.address),no_arguments);
    return true; // Dispatch returned; caller must verify outcome and never retry uncertainty.
}
}
