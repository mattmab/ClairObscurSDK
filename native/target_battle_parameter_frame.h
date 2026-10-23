#pragma once
#include "battle_parameter_frame.h"
#include "target_pod_schema.h"
#include <cstring>

// Private FBattleStartParams engine binding. The containing pinned runtime
// supplies executable fingerprint/SEH containment, persistent frame ownership,
// source allowlist proof and registered leases. Not a raw-address wire API.
namespace e33_enemy_spawn {
struct ParameterEngineEntry {uint64_t rva;uint8_t prefix[32];};
inline constexpr ParameterEngineEntry parameter_engine_entries[]={
 {0x3dd9770,{0x48,0x89,0x5c,0x24,0x18,0x55,0x56,0x57,0x48,0x83,0xec,0x20,0x48,0x8d,0xb1,0xd8,0x00,0x00,0x00,0x41,0x8b,0xe8,0x48,0x8b,0x06,0x48,0x8b,0xf9,0x48,0x8b,0xce,0x48}},
 {0x127a110,{0x40,0x53,0x41,0x54,0x41,0x55,0x41,0x56,0x41,0x57,0x48,0x83,0xec,0x40,0x44,0x8b,0x51,0x5c,0x4d,0x8b,0xf0,0x44,0x8b,0x69,0x58,0x4c,0x8b,0xfa,0x41,0xff,0xcd,0x45}},
 {0x127ae90,{0x4c,0x8b,0xdc,0x55,0x41,0x54,0x41,0x57,0x48,0x83,0xec,0x60,0x48,0x8b,0x05,0x1d,0x03,0xf8,0x07,0x48,0x33,0xc4,0x48,0x89,0x44,0x24,0x38,0xf7,0x81,0xb0,0x00,0x00}}
};

template<class Pool> struct TargetBattleParameterOps {
    uint64_t base,session;
    Pool& leases;
    CallIdentity structure,source,root;
    uint64_t struct_lease,source_lease,root_lease;
    // Owner proves exact audited source path/root relationship, never names alone.
    void* owner;
    bool (*allowed_source)(void*,const CallIdentity&,const CallIdentity&);

    bool valid(const CallIdentity& id)const {
        return TargetPodSchemaOps{base}.identity(id);
    }
    bool named(uint64_t object,const char* name,const char* package)const {
        const auto id=call_capture(base,object);
        if(!valid(id)||!exact_name(base,object+24,name))return false;
        const auto outer=call_capture(base,local_read<uint64_t>(object+32));
        return valid(outer)&&exact_name(base,outer.address+24,package);
    }
    uint64_t field(uint64_t structure_at,const char* name,uint32_t offset,uint32_t size,uint64_t table,uint64_t flags)const {
        unsigned walked=0,matches=0;uint64_t result=0;
        for(auto p=local_read<uint64_t>(structure_at+0x50);p&&++walked<=128;p=local_read<uint64_t>(p+0x18)){
            if(!exact_name(base,p+0x20,name))continue;
            ++matches;
            if(local_read<uint64_t>(p)==base+table&&local_read<uint64_t>(p+0x10)==(structure_at|1)&&
               local_read<uint32_t>(p+0x30)==1&&local_read<uint32_t>(p+0x34)==size&&
               local_read<uint64_t>(p+0x38)==flags&&local_read<uint32_t>(p+0x44)==offset)result=p;
        }
        return walked<=128&&matches==1?result:0;
    }
    bool engine_profile_ready()const {
        if(!TargetPodSchemaOps{base}.context()||!session||!valid(structure)||
           !named(structure.address,"FBattleStartParams","/Game/Gameplay/Battle/FBattleStartParams")||
           !named(local_read<uint64_t>(structure.address+16),"UserDefinedStruct","/Script/Engine")||
           local_read<uint32_t>(structure.address+0x58)!=344||
           local_read<uint32_t>(structure.address+0x5c)!=8||
           local_read<uint64_t>(structure.address)!=base+0x7538708||
           local_read<uint64_t>(base+0x7538708+0x300)!=base+parameter_engine_entries[0].rva||
           local_read<uint64_t>(base+0x7538708+0x308)!=base+parameter_engine_entries[2].rva)return false;
        for(const auto& entry:parameter_engine_entries)
            if(std::memcmp(reinterpret_cast<const void*>(base+entry.rva),entry.prefix,sizeof(entry.prefix)))return false;
        return true;
    }
    bool engine_ready()const {
        return engine_profile_ready()&&leases.owns_object(session,struct_lease,structure.address);
    }
    bool source_profile_ready()const {
        if(!engine_profile_ready()||!owner||!allowed_source||!valid(source)||!valid(root)||
           !allowed_source(owner,root,source)||source.address==root.address||
           local_read<uint32_t>(source.address+8)&0x30)return false;
        const auto cls=local_read<uint64_t>(source.address+16);
        if(!call_is_class(base,cls)||!named(cls,"BP_GameAction_TriggerBattle_C",
            "/Game/Gameplay/GameActionsSystem/TriggerBattle/BP_GameAction_TriggerBattle"))return false;
        auto outer=local_read<uint64_t>(source.address+32);unsigned walked_outers=0;
        for(;outer&&outer!=root.address&&++walked_outers<64;outer=local_read<uint64_t>(outer+32))
            if(!valid(call_capture(base,outer)))return false;
        if(outer!=root.address)return false;
        unsigned walked=0,matches=0;uint64_t field=0;
        for(auto p=local_read<uint64_t>(cls+0x50);p&&++walked<=128;p=local_read<uint64_t>(p+0x18)) {
            if(!exact_name(base,p+0x20,"Battle Start Params"))continue;
            field=p;++matches;
        }
        return walked<=128&&matches==1&&field&&
            local_read<uint64_t>(field)==base+0x6e136a0&&
            local_read<uint64_t>(field+0x10)==(cls|1)&&
            local_read<uint32_t>(field+0x30)==1&&local_read<uint32_t>(field+0x34)==344&&
            local_read<uint64_t>(field+0x38)==2252349569499141ULL&&
            local_read<uint32_t>(field+0x44)==48&&local_read<uint64_t>(field+0x70)==structure.address;
    }
    bool preflight()const {
        return engine_ready()&&source_profile_ready()&&
            leases.owns_object(session,source_lease,source.address)&&
            leases.owns_object(session,root_lease,root.address);
    }
    bool cleanup_ready()const{return engine_ready();}
    bool destination_separate(void* destination)const {
        return parameter_destination_separate(reinterpret_cast<uintptr_t>(destination),source.address);
    }
    ParameterCall initialize(void* destination)const {
        if(!destination_separate(destination)||!preflight())return ParameterCall::NotDispatched;
        reinterpret_cast<void(__fastcall*)(void*,void*,int)>(base+parameter_engine_entries[0].rva)(
            reinterpret_cast<void*>(structure.address),destination,1);
        return ParameterCall::Completed;
    }
    ParameterCall copy(void* destination)const {
        if(!destination_separate(destination)||!preflight())return ParameterCall::NotDispatched;
        reinterpret_cast<void(__fastcall*)(void*,void*,const void*,int)>(base+parameter_engine_entries[1].rva)(
            reinterpret_cast<void*>(structure.address),destination,reinterpret_cast<const void*>(source.address+48),1);
        return ParameterCall::Completed;
    }
    ParameterCall destroy(void* destination)const {
        if(!destination_separate(destination)||!cleanup_ready())return ParameterCall::NotDispatched;
        reinterpret_cast<void(__fastcall*)(void*,void*,int)>(base+parameter_engine_entries[2].rva)(
            reinterpret_cast<void*>(structure.address),destination,1);
        return ParameterCall::Completed;
    }
};
}
