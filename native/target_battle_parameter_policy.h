#pragma once
#include "battle_parameter_policy.h"
#include "target_battle_parameter_frame.h"

namespace e33_enemy_spawn {
// Private binding only. The instance-name callback must prove an existing
// SDK-owned actor and its registered lease, never accept a caller-supplied name.
template<class Pool> struct TargetBattleParameterPolicyOps {
    TargetBattleParameterOps<Pool> frame;
    ParameterPolicy policy;
    void* instance_owner;
    bool (*owns_instance_name)(void*,uint64_t);

    uint64_t field(uint64_t structure,const char* name,uint32_t offset,uint32_t size,
        uint64_t table,uint64_t flags)const {
        return frame.field(structure,name,offset,size,table,flags);
    }
    uint64_t party_field()const {
        return field(frame.structure.address,"OverrideParty_63_56C3E35647CCE3DAC58BE292F8A3FFC0",200,16,0x6e0de80,5);
    }
    bool array_valid(const void* destination)const {
        const auto at=reinterpret_cast<uint64_t>(destination)+200;
        const auto data=local_read<uint64_t>(at);
        const auto count=local_read<int32_t>(at+8),capacity=local_read<int32_t>(at+12);
        return count>=0&&count<=64&&capacity>=count&&capacity<=4096&&
            (capacity?(data&&!(data&3)):!data);
    }
    bool preflight(void* destination,const ParameterPolicy& requested)const {
        if(!frame.preflight()||!frame.destination_separate(destination)||!instance_owner||!owns_instance_name||
           requested.mode!=policy.mode||requested.instance_name!=policy.instance_name||
           !owns_instance_name(instance_owner,requested.instance_name))return false;
        const auto structure=frame.structure.address;
        const auto name=field(structure,"EnemyGlobalID_12_57EC6FC84879C6C042EC7BB68F507FE2",16,8,0x6e13040,0x8001040000205ULL);
        const auto wrapper=field(structure,"GameActionPostBattleWrapper_45_A2233C9E408877A1A0FE07B484DD564D",168,16,0x6e136a0,0x9040000205ULL);
        const auto legacy=field(structure,"GameActionPostBattle_35_61E2AECF4179AB60F99ABCB5EA5BB96F",184,8,0x6e11d38,0x8001000010205ULL);
        if(!name||!wrapper||!legacy||!frame.named(local_read<uint64_t>(legacy+0x70),"BP_PDT_GameAction_C","/Game/Gameplay/GameActionsSystem/BP_PDT_GameAction"))return false;
        const auto wrapper_type=local_read<uint64_t>(wrapper+0x70);
        if(!frame.named(wrapper_type,"GameAction_Wrapper","/Script/SandFall")||local_read<uint32_t>(wrapper_type+0x58)!=16)return false;
        const auto reference=field(wrapper_type,"GameActionReference",0,8,0x6e11d38,0x18001000000205ULL);
        const auto inlined=field(wrapper_type,"GameActionInline",8,8,0x6e11d38,0x1a00100008020dULL);
        if(!reference||!inlined||!frame.named(local_read<uint64_t>(reference+0x70),"GameAction","/Script/SandFall")||
           local_read<uint64_t>(reference+0x70)!=local_read<uint64_t>(inlined+0x70))return false;
        if(requested.mode==ParameterPolicyMode::OriginalParameters)return true;
        const auto party=party_field();
        if(!party||!array_valid(destination)||(local_read<uint8_t>(party+0x70)&1))return false;
        const auto inner=local_read<uint64_t>(party+0x78);
        if(!inner||local_read<uint64_t>(inner)!=frame.base+0x6e136a0||local_read<uint64_t>(inner+0x10)!=party||
           !exact_name(frame.base,inner+0x20,"OverrideParty_63_56C3E35647CCE3DAC58BE292F8A3FFC0")||
           local_read<uint32_t>(inner+0x30)!=1||local_read<uint32_t>(inner+0x34)!=12||local_read<uint32_t>(inner+0x44)!=0)return false;
        const auto slot=local_read<uint64_t>(inner+0x70);
        if(!frame.named(slot,"S_jRPG_PartySlot","/Game/jRPGTemplate/Structures/S_jRPG_PartySlot")||
           !supported_party_slot_layout(local_read<uint32_t>(slot+0x58),local_read<uint32_t>(slot+0x5c),
                local_read<uint32_t>(inner+0x34),local_read<uint64_t>(inner+0x38)))return false;
        static constexpr uint8_t prefix[]={0x48,0x89,0x5c,0x24,0x08,0x48,0x89,0x6c,0x24,0x10,0x48,0x89,0x74,0x24,0x18,0x48,0x89,0x7c,0x24,0x20,0x41,0x56,0x48,0x83,0xec,0x40,0x0f,0xb6,0x71,0x70,0x48,0x8b};
        return local_read<uint64_t>(frame.base+0x6e0de80+0x130)==frame.base+0x1339690&&
            !std::memcmp(reinterpret_cast<const void*>(frame.base+0x1339690),prefix,sizeof(prefix));
    }
    ParameterCall clear_party(void* destination)const {
        if(policy.mode!=ParameterPolicyMode::Isolated||!preflight(destination,policy))return ParameterCall::NotDispatched;
        reinterpret_cast<void(__fastcall*)(void*,void*)>(frame.base+0x1339690)(
            reinterpret_cast<void*>(party_field()),static_cast<uint8_t*>(destination)+200);
        return array_valid(destination)&&local_read<int32_t>(reinterpret_cast<uint64_t>(destination)+208)==0?
            ParameterCall::Completed:ParameterCall::Unknown;
    }
    bool verify(const void* destination,const ParameterPolicy& requested)const {
        if(!frame.preflight()||!owns_instance_name(instance_owner,requested.instance_name)||
           local_read<uint64_t>(reinterpret_cast<uint64_t>(destination)+16)!=requested.instance_name)return false;
        if(requested.mode==ParameterPolicyMode::OriginalParameters)return true;
        const auto at=reinterpret_cast<uint64_t>(destination);
        if(local_read<uint64_t>(at+168)||local_read<uint64_t>(at+176)||local_read<uint64_t>(at+184)||!array_valid(destination))return false;
        if(requested.mode==ParameterPolicyMode::Isolated)return local_read<int32_t>(at+208)==0;
        if(requested.mode!=ParameterPolicyMode::AuthoredParty)return false;
        const auto source_frame=frame.source.address+48;
        if(!array_valid(reinterpret_cast<const void*>(source_frame)))return false;
        const auto count=local_read<int32_t>(source_frame+208);
        if(count!=1||local_read<int32_t>(at+208)!=count)return false;
        const auto from=local_read<uint64_t>(source_frame+200),to=local_read<uint64_t>(at+200);
        return from&&to&&from!=to&&!std::memcmp(reinterpret_cast<const void*>(from),reinterpret_cast<const void*>(to),12);
    }
    ParameterCall apply(void* destination){return apply_parameter_policy(*this,destination,policy);}
};
}
