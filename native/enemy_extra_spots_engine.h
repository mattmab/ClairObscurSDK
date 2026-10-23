#pragma once
#include "enemy_extra_spots.h"
#include "enemy_arena_assembly.h"
#include "stable_identity.h"
#include "runtime_cinematic_profile.h"
#pragma warning(push)
#pragma warning(disable:4324) // Engine Transform call frames require 16-byte alignment.

namespace e33_enemy_spawn {
struct ExtraSpotRecord {
    CallIdentity component{},child{};
    uint64_t component_lease=0,child_lease=0;
    bool destroyed=false;
    bool creation_dispatched=false,creation_acknowledged=false;
    alignas(16) uint8_t creation_frame[128]{};
};
struct ExtraSpotsEngineState {
    CallIdentity world{},actor{},arena{},component_class{},spot_class{};
    // AddComponentByClass, FinishAddComponent, SetChildActorClass,
    // K2_DestroyComponent and GetAllChildActors, respectively.
    CallIdentity functions[5]{};
    ExtraSpotsTransaction<ExtraSpotRecord> transaction;
};

inline const MeshField extra_set_child_fields[]={
    {"InClass","ClassProperty",0,8,0x1c001000000280ULL,0x6e12ac8ULL,"","",0,"",0,"Actor"}};
inline const MeshFunction extra_set_child={"ChildActorComponent","SetChildActorClass",0x4020401,8,8,65535,0x3571710,extra_set_child_fields,1};
inline const MeshField extra_children_fields[]={
    {"ChildActors","ArrayProperty",0,16,0x10000000000380ULL,0x6e0de80ULL,"","ObjectProperty",8,"",0,""},
    {"bIncludeDescendants","BoolProperty",16,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshFunction extra_children={"Actor","GetAllChildActors",0x54420403,17,24,65535,0x3339e40,extra_children_fields,2};

// Compile-time profiles only. This does not expose caller-controlled layouts or
// pointers, and reuses the shipping SDK's existing profile/schema validators.
inline bool extra_function(uint64_t b,CallIdentity identity,const MeshFunction& p){
    const auto fn=call_identity(b,identity);
    return fn&&e33_mesh::named(b,local_read<uint64_t>(fn+32),p.owner,"/Script/Engine")&&
        exact_name(b,fn+24,p.name)&&local_read<uint32_t>(fn+0xb0)==p.flags&&
        local_read<uint16_t>(fn+0xb6)==p.params&&local_read<uint16_t>(fn+0xb8)==p.returned&&
        local_read<int32_t>(fn+0x58)==int(p.extent)&&local_read<uint64_t>(fn+0xd8)==b+p.entry&&
        e33_mesh::fields(b,fn,p.fields,p.count);
}
inline bool extra_dispatch(uint64_t b,CallIdentity recipient,CallIdentity function,
                           const MeshFunction& profile,void* frame){
    if(!TargetPodSchemaOps{b}.context()||!extra_function(b,function,profile))return false;
    const auto object=call_identity(b,recipient),fn=call_identity(b,function);
    if(!object||!call_derives(b,local_read<uint64_t>(object+16),local_read<uint64_t>(fn+32)))return false;
    const auto pe=local_read<uint64_t>(local_read<uint64_t>(object)+0x268);
    if(pe!=b+0x1393330&&pe!=b+0x332bb90)return false;
    reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(pe)(reinterpret_cast<void*>(object),reinterpret_cast<void*>(fn),frame);
    return true;
}

template<class Pool>
class EngineExtraSpots {
    uint64_t base_,session_;
    Pool& pool_;
    ExtraSpotsEngineState& state_;
    bool identity(CallIdentity id)const{return call_identity(base_,id)==id.address&&id.address;}
    bool context()const{
        return TargetPodSchemaOps{base_}.context()&&identity(state_.world)&&identity(state_.actor)&&identity(state_.arena)&&
            arena_world(base_,state_.actor.address,state_.world.address)&&arena_world(base_,state_.arena.address,state_.world.address);
    }
    bool out_of_battle()const{
        const auto at=picto_field(base_,state_.actor.address,"IsInBattle","BoolProperty",2930,1);
        return at&&local_read<uint8_t>(at)==0;
    }
    bool retain(CallIdentity& object,uint64_t& token){
        TargetStrongReferenceOps ops{base_,object};
        return pool_.acquire(ops,session_,object.address,token)==StrongLeaseResult::Ok&&
            stabilize_retained_identity(ops,object);
    }
    bool release(uint64_t& token){
        if(!token)return true;
        TargetStrongReferenceOps ops{base_,{-1,0,0}};
        if(pool_.release(ops,session_,token)!=StrongLeaseResult::Ok)return false;
        token=0;return true;
    }
    bool owned_component(CallIdentity component)const{
        return identity(component)&&arena_class(base_,component.address,"ChildActorComponent","/Script/Engine")&&
            local_read<uint64_t>(component.address+32)==state_.arena.address;
    }
public:
    EngineExtraSpots(uint64_t base,uint64_t session,Pool& pool,ExtraSpotsEngineState& state):
        base_(base),session_(session),pool_(pool),state_(state){}
    bool preflight(uint32_t total){
        if(total<5||total>10||!context()||!out_of_battle()||!identity(state_.component_class)||!identity(state_.spot_class)||
           !call_is_class(base_,state_.component_class.address)||!call_is_class(base_,state_.spot_class.address)||
           !e33_mesh::named(base_,state_.component_class.address,"ChildActorComponent","/Script/Engine")||
           !e33_mesh::named(base_,state_.spot_class.address,"BP_jRPG_EnemyBattleSpot_C",
               "/Game/jRPGTemplate/Blueprints/Other/Battle/BP_jRPG_EnemyBattleSpot"))return false;
        ArenaAssemblyObservation observed{};
        if(observe_arena_assembly(base_,state_.world.address,state_.arena.address,observed)||observed.enemy_mask!=15)return false;
        if(!e33_mesh::function(base_,state_.functions[0],2)||!e33_mesh::function(base_,state_.functions[1],3)||
           !extra_function(base_,state_.functions[2],extra_set_child)||
           !extra_function(base_,state_.functions[3],e33_runtime_cinematic::demo_functions[7])||
           !extra_function(base_,state_.functions[4],extra_children))return false;
        return pool_.preflight(session_,12)==StrongLeaseResult::Ok;
    }
    bool cleanup_ready(){
        if(!TargetPodSchemaOps{base_}.context())return false;
        // A destroyed owner no longer has an active encounter. Explicitly
        // destroyed components are skipped below, but retained leases survive
        // until engine-safe release is acknowledged.
        return !identity(state_.actor)||!arena_live(base_,state_.actor.address)||out_of_battle();
    }
    bool create(uint32_t slot,ExtraSpotRecord& record){
        if(slot<4||slot>9||!context()||!out_of_battle())return false;
        auto* frame=record.creation_frame;
        double transform[12]={0,0,1,0,1000.+500.*((slot-4)/3),
            -48.27496337890619+450.*(int((slot-4)%3)-1),0,0,1,1,1,0};
        std::memcpy(frame,&state_.component_class.address,8);
        std::memcpy(frame+16,transform,96);frame[112]=1;
        record.creation_dispatched=true;
        if(!e33_mesh::dispatch(base_,state_.arena,state_.functions[0],2,frame)){
            record.creation_dispatched=false;return false;
        }
        record.creation_acknowledged=true;
        // Journal the returned pointer before validation, retention or any
        // construction call that can fail after allocating engine objects.
        record.component=call_capture(base_,local_read<uint64_t>(reinterpret_cast<uint64_t>(frame+120)));
        if(!owned_component(record.component)||!retain(record.component,record.component_lease))return false;
        std::memset(frame,0,128);std::memcpy(frame,&state_.spot_class.address,8);
        if(!extra_dispatch(base_,record.component,state_.functions[2],extra_set_child,frame))return false;
        std::memset(frame,0,128);std::memcpy(frame,&record.component.address,8);std::memcpy(frame+16,transform,96);
        if(!e33_mesh::dispatch(base_,state_.arena,state_.functions[1],3,frame))return false;
        if(!owned_component(record.component))return false;
        record.child=call_capture(base_,arena_reference(base_,record.component.address,"ChildActor",568));
        if(!identity(record.child)||!arena_class(base_,record.child.address,"BP_jRPG_EnemyBattleSpot_C",
             "/Game/jRPGTemplate/Blueprints/Other/Battle/BP_jRPG_EnemyBattleSpot")||
           !arena_world(base_,record.child.address,state_.world.address)||!retain(record.child,record.child_lease))return false;
        const auto index=picto_field(base_,record.child.address,"SlotIndex","IntProperty",712,4);
        const auto position=arena_reference(base_,record.child.address,"SpawnPosition",664);
        const auto arrow=arena_reference(base_,record.child.address,"Arrow",688);
        if(!index||!arena_scene(base_,position,record.child.address)||!arena_scene(base_,arrow,record.child.address))return false;
        const auto value=int32_t(slot);
        std::memcpy(reinterpret_cast<void*>(index),&value,4);
        return local_read<int32_t>(index)==value;
    }
    bool verify(uint64_t required){
        if(!context()||!out_of_battle())return false;
        alignas(8) uint8_t frame[24]{};
        if(!extra_dispatch(base_,state_.arena,state_.functions[4],extra_children,frame))return false;
        const auto data=local_read<uint64_t>(reinterpret_cast<uint64_t>(frame));
        const auto count=local_read<int32_t>(reinterpret_cast<uint64_t>(frame+8));
        const auto capacity=local_read<int32_t>(reinterpret_cast<uint64_t>(frame+12));
        bool valid=count>=0&&count<=128&&capacity>=count&&capacity<=4096&&(!count||(data>=0x10000&&!(data&7)));
        uint64_t mask=0;
        for(int32_t i=0;valid&&i<count;++i){
            const auto child=local_read<uint64_t>(data+uint64_t(i)*8);
            if(!arena_class(base_,child,"BP_jRPG_EnemyBattleSpot_C",
                "/Game/jRPGTemplate/Blueprints/Other/Battle/BP_jRPG_EnemyBattleSpot"))continue;
            const auto field=picto_field(base_,child,"SlotIndex","IntProperty",712,4);
            const auto index=field?local_read<int32_t>(field):-1;
            if(index<0||index>=64||(mask&(uint64_t(1)<<index))){valid=false;break;}
            mask|=uint64_t(1)<<index;
        }
        // Same established engine-owned array ABI used by the SDK's existing
        // bound-object query. Never free this engine result with the CRT.
        if(data)reinterpret_cast<void(__fastcall*)(void*)>(base_+0x107c7d0)(reinterpret_cast<void*>(data));
        return valid&&(mask&required)==required;
    }
    bool retire(ExtraSpotRecord& record){
        if(!cleanup_ready())return false;
        if(record.creation_dispatched&&!record.creation_acknowledged){
            // A native exception may have occurred after allocation but before
            // return. Preserve this record instead of treating null as proof
            // that nothing happened. No creation is ever replayed.
            const auto output=local_read<uint64_t>(reinterpret_cast<uint64_t>(record.creation_frame+120));
            if(!output)return false;
            record.component=call_capture(base_,output);
            if(!owned_component(record.component))return false;
            record.creation_acknowledged=true;
        }
        return retire_extra_spot_record(record,*this);
    }
    bool component_current(const ExtraSpotRecord& record)const{return identity(record.component);}
    bool component_live(const ExtraSpotRecord& record)const{return arena_live(base_,record.component.address);}
    bool destroy_owned(const ExtraSpotRecord& record){
        if(!owned_component(record.component)||!identity(state_.arena))return false;
        const auto child=arena_reference(base_,record.component.address,"ChildActor",568);
        if(record.child.address&&child&&child!=record.child.address)return false;
        alignas(8) uint8_t frame[8]{};std::memcpy(frame,&state_.arena.address,8);
        return extra_dispatch(base_,record.component,state_.functions[3],e33_runtime_cinematic::demo_functions[7],frame);
    }
    bool release_child(ExtraSpotRecord& record){return release(record.child_lease);}
    bool release_component(ExtraSpotRecord& record){return release(record.component_lease);}
};
}
#pragma warning(pop)
