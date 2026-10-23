#pragma once
#include "target_battle_parameter_frame.h"
#include "battle_entry_copy_stub.h"

namespace e33_enemy_spawn {
// Private supported-build binding, not a public raw-struct invocation API.
// The containing persistent owner supplies independently retained manager and
// function leases plus exact world/controller/arena/policy authority. Its proof
// must also establish that parameters points to that owner's policy-applied
// frame. No default or caller-supplied wire proof is accepted.
template<class Pool> struct TargetBattleEntryOps {
    TargetBattleParameterOps<Pool> frame;
    CallIdentity manager,function;
    uint64_t manager_lease,function_lease;
    void* owner;
    bool (*allowed_entry)(void*,const void*,const CallIdentity&,const CallIdentity&);
    const void* returned_parameters=nullptr;
    bool (*before_entry)(void*,const void*,const CallIdentity&,const CallIdentity&)=nullptr;

    bool copy_profile_ready(BattleEntryCopyStub& stub)const {
        if(!frame.preflight()||!frame.valid(manager)||!frame.valid(function)||
           !frame.leases.owns_object(frame.session,manager_lease,manager.address)||
           !frame.leases.owns_object(frame.session,function_lease,function.address))return false;
        const auto b=frame.base,cls=local_read<uint64_t>(manager.address+16);
        if(!frame.named(cls,"AC_jRPG_BattleManager_C","/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_BattleManager")||
           local_read<uint64_t>(function.address+32)!=cls)return false;
        const auto script=local_read<uint64_t>(function.address+0x60);
        const auto count=local_read<int32_t>(function.address+0x68),capacity=local_read<int32_t>(function.address+0x6c);
        if(script<0x10000||count!=36||capacity<count||capacity>65536||
           !decode_battle_entry_copy_stub(reinterpret_cast<const void*>(script),36,stub)||
           stub.source!=local_read<uint64_t>(function.address+0x50))return false;
        const auto graph=stub.graph,destination=stub.destination;
        if(!frame.valid(call_capture(b,graph))||local_read<uint64_t>(graph+32)!=cls||
           !frame.named(local_read<uint64_t>(graph+16),"Function","/Script/CoreUObject")||
           !exact_name(b,graph+24,"ExecuteUbergraph_AC_jRPG_BattleManager")||
           local_read<uint32_t>(graph+0xb0)!=0x808001||local_read<uint16_t>(graph+0xb6)!=4||
           local_read<uint16_t>(graph+0xb8)!=65535||local_read<uint32_t>(graph+0x58)!=10028||
           local_read<uint64_t>(graph+0xd8)!=b+0x13937a0||
           local_read<uint64_t>(destination)!=b+0x6e136a0||local_read<uint64_t>(destination+0x10)!=(graph|1)||
           !exact_name(b,destination+0x20,"K2Node_CustomEvent_BattleStartParams")||
           local_read<uint32_t>(destination+0x30)!=1||local_read<uint32_t>(destination+0x34)!=344||
           local_read<uint64_t>(destination+0x38)!=0x8008000000000ULL||
           local_read<uint32_t>(destination+0x44)!=2288||local_read<uint64_t>(destination+0x70)!=frame.structure.address)return false;
        // Establish that the bytecode operand is actually in this graph's field
        // chain, not merely an object that resembles its expected property.
        unsigned walked=0,matches=0;
        for(auto field=local_read<uint64_t>(graph+0x50);field&&++walked<=2048;field=local_read<uint64_t>(field+0x18))
            if(field==destination)++matches;
        if(walked>2048||matches!=1)return false;
        const auto persistent=local_read<uint64_t>(cls+0x50);
        if(!persistent||local_read<uint64_t>(persistent)!=b+0x6e136a0||
           local_read<uint64_t>(persistent+0x10)!=(cls|1)||!exact_name(b,persistent+0x20,"UberGraphFrame")||
           local_read<uint32_t>(persistent+0x30)!=1||local_read<uint32_t>(persistent+0x34)!=8||
           local_read<uint64_t>(persistent+0x38)!=0x202200||local_read<uint32_t>(persistent+0x44)!=160||
           !frame.named(local_read<uint64_t>(persistent+0x70),"PointerToUberGraphFrame","/Script/Engine"))return false;
        static constexpr uint8_t let_prefix[]={0x48,0x89,0x5c,0x24,0x08,0x57,0x48,0x83,0xec,0x20,0x33,0xc0,0x48,0x8b,0xfa,0x48,0x89,0x42,0x30,0x48,0x89,0x42,0x38,0x48,0x89,0x42,0x40,0x48,0x8b,0x42,0x20,0x48};
        static constexpr uint8_t copy_tail[]={0x48,0x63,0x41,0x44,0x4c,0x8b,0x42,0x28,0x49,0x03,0xc0,0x4c,0x89,0x42,0x40,0x48,0x89,0x42,0x38,0x4d,0x85,0xc9,0x74,0x0c,0x48,0x8b,0x01,0x49,0x8b,0xd1,0xff,0x90,0x10,0x01,0x00,0x00};
        static constexpr uint8_t struct_copy[]={0x48,0x8b,0x49,0x70,0xe9,0x47,0x14,0xf1,0xff};
        static constexpr uint8_t property_copy[]={0x48,0x89,0x5c,0x24,0x08,0x48,0x89,0x74,0x24,0x10,0x57,0x48,0x83,0xec,0x20,0x48,0x8b,0x01,0x49,0x8b,0xf0,0x48,0x8b,0xfa,0x48,0x8b,0xd9,0xff,0x90,0x80,0x00,0x00};
        static constexpr uint8_t property_copy_tail[]={0x48,0x8b,0x03,0x4c,0x8b,0xc1,0x44,0x8b,0x4b,0x30,0x48,0x8b,0xd7,0x48,0x8b,0xcb,0xff,0x90,0xf0,0x00,0x00,0x00};
        return local_read<uint64_t>(b+0x9360600+0x64*8)==b+0x13983f0&&
            local_read<uint64_t>(b+0x9360600)==b+0x1398750&&
            BlueprintDirectTrace::original_direct_or_owned(b,local_read<uint64_t>(b+0x9360600+0x46*8))&&
            local_read<uint64_t>(b+0x6e136a0+0x80)==b+0x10044f0&&
            local_read<uint8_t>(b+0x10044f0)==0x32&&local_read<uint8_t>(b+0x10044f1)==0xc0&&local_read<uint8_t>(b+0x10044f2)==0xc3&&
            local_read<uint64_t>(b+0x6e136a0+0xf0)==b+0x1368cc0&&
            local_read<uint64_t>(b+0x6e136a0+0x110)==b+0x133a600&&
            !std::memcmp(reinterpret_cast<const void*>(b+0x13983f0),let_prefix,sizeof(let_prefix))&&
            !std::memcmp(reinterpret_cast<const void*>(b+0x1398812),copy_tail,sizeof(copy_tail))&&
            !std::memcmp(reinterpret_cast<const void*>(b+0x1368cc0),struct_copy,sizeof(struct_copy))&&
            !std::memcmp(reinterpret_cast<const void*>(b+0x133a600),property_copy,sizeof(property_copy))&&
            !std::memcmp(reinterpret_cast<const void*>(b+0x133a683),property_copy_tail,sizeof(property_copy_tail));
    }

    bool entry_preflight(const void* parameters)const {
        if(!parameters||!owner||!allowed_entry||!frame.preflight()||
           !frame.destination_separate(const_cast<void*>(parameters))||
           !frame.valid(manager)||!frame.valid(function)||
           !frame.leases.owns_object(frame.session,manager_lease,manager.address)||
           !frame.leases.owns_object(frame.session,function_lease,function.address)||
           (local_read<uint32_t>(manager.address+8)&0x30)||
           !allowed_entry(owner,parameters,manager,function))return false;
        const auto cls=local_read<uint64_t>(manager.address+16);
        if(!call_is_class(frame.base,cls)||!frame.named(cls,"AC_jRPG_BattleManager_C",
            "/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_BattleManager")||
           local_read<uint64_t>(function.address+32)!=cls||
           !frame.named(local_read<uint64_t>(function.address+16),"Function","/Script/CoreUObject")||
           !exact_name(frame.base,function.address+24,"StartBattleNEW")||
           local_read<uint32_t>(function.address+0xb0)!=0xc000000||
           local_read<uint16_t>(function.address+0xb6)!=344||
           local_read<uint16_t>(function.address+0xb8)!=65535||
           local_read<uint32_t>(function.address+0x58)!=344||
           local_read<uint64_t>(function.address+0xd8)!=frame.base+0x13937a0)return false;
        const auto field=local_read<uint64_t>(function.address+0x50);
        if(!field||local_read<uint64_t>(field+0x18)||
           local_read<uint64_t>(field)!=frame.base+0x6e136a0||
           local_read<uint64_t>(field+0x10)!=(function.address|1)||
           !exact_name(frame.base,field+0x20,"BattleStartParams")||
           local_read<uint32_t>(field+0x30)!=1||local_read<uint32_t>(field+0x34)!=344||
           local_read<uint64_t>(field+0x38)!=0x8008000000094ULL||
           local_read<uint32_t>(field+0x44)!=0||
           local_read<uint64_t>(field+0x70)!=frame.structure.address)return false;
        const auto pe=local_read<uint64_t>(local_read<uint64_t>(manager.address)+0x268);
        BattleEntryCopyStub stub;
        return (pe==frame.base+0x1393330||pe==frame.base+0x332bb90)&&copy_profile_ready(stub);
    }
    ParameterCall invoke_entry(const void* parameters) {
        if(returned_parameters)return ParameterCall::NotDispatched;
        if(!entry_preflight(parameters))return ParameterCall::NotDispatched;
        if(before_entry&&!before_entry(owner,parameters,manager,function))return ParameterCall::NotDispatched;
        const auto pe=local_read<uint64_t>(local_read<uint64_t>(manager.address)+0x268);
        reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(pe)(
            reinterpret_cast<void*>(manager.address),reinterpret_cast<void*>(function.address),
            const_cast<void*>(parameters));
        returned_parameters=parameters;
        // This says only that ProcessEvent returned. Battle startup is latent.
        return ParameterCall::Completed;
    }
    bool owned_parameter_copy_ready(const void* parameters)const {
        if(!parameters||parameters!=returned_parameters)return false;
        BattleEntryCopyStub stub;
        if(!copy_profile_ready(stub))return false;
        const auto data=local_read<uint64_t>(manager.address+160);
        const auto input=reinterpret_cast<uint64_t>(parameters);
        if(data<0x10000||(data&7)||data>UINT64_MAX-10028||input>UINT64_MAX-344)return false;
        const auto destination=data+2288;
        if(!(destination+344<=input||input+344<=destination)||
           std::memcmp(parameters,reinterpret_cast<const void*>(destination),24))return false;
        const auto from=local_read<uint64_t>(input+200),to=local_read<uint64_t>(destination+200);
        const auto count=local_read<int32_t>(input+208),copy_count=local_read<int32_t>(destination+208);
        const auto capacity=local_read<int32_t>(destination+212);
        if(count<0||count>64||copy_count!=count||capacity<count||capacity>4096)return false;
        if(!count)return true;
        const auto extent=uint64_t(count)*12;
        if(from<0x10000||to<0x10000||(from&3)||(to&3)||from>UINT64_MAX-extent||to>UINT64_MAX-extent||
           !(from+extent<=to||to+extent<=from))return false;
        // PartySlot declares 9 bytes at a 12-byte array stride. Padding is not
        // value data and need not be copied by the original struct operation.
        for(int32_t i=0;i<count;++i)
            if(std::memcmp(reinterpret_cast<const void*>(from+uint64_t(i)*12),reinterpret_cast<const void*>(to+uint64_t(i)*12),9))return false;
        return true;
    }
};
}
