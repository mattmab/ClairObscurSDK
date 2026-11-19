#pragma once
#include "defeat_delay_override.h"
#include "mesh_owner.h"
#include "target_pod_schema.h"
template<class Pool> struct TargetDefeatDelayOps {
    uint64_t base,session;Pool& leases;
    uint32_t bits(uint64_t at)const{return local_read<uint32_t>(at);}
    void write(uint64_t at,uint32_t value)const{std::memcpy(reinterpret_cast<void*>(at),&value,4);}
    bool resolve(const e33_defeat_delay::Packet& p,uint64_t& at)const{
        if(!TargetPodSchemaOps{base}.context()||!leases.owns_object(session,p.token,p.function.address))return false;
        const auto f=call_identity(base,p.function);
        if(!f||!e33_mesh::named(base,local_read<uint64_t>(f+16),"Function","/Script/CoreUObject")||
           !exact_name(base,f+24,"ExecuteUbergraph_AC_jRPG_BattleManager"))return false;
        const auto owner=local_read<uint64_t>(f+32);
        if(!e33_mesh::named(base,owner,"AC_jRPG_BattleManager_C","/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_BattleManager")||
           local_read<uint32_t>(f+0xb0)!=0x808001||local_read<uint16_t>(f+0xb6)!=4||
           local_read<uint16_t>(f+0xb8)!=65535||local_read<uint64_t>(f+0xd8)!=base+0x13937a0)return false;
        struct Array{uint64_t data;int32_t count,capacity;};
        const auto script=local_read<Array>(f+0x60);
        if(!script.data||script.count!=69737||script.capacity<script.count||script.capacity>262144)return false;
        const auto b=script.data;
        if(local_read<uint8_t>(b+54896)!=0x68||local_read<uint8_t>(b+54906)!=0x1e||
           local_read<uint8_t>(b+54911)!=0x2f||local_read<uint32_t>(b+54920)!=32||
           local_read<uint8_t>(b+54924)!=0x5b||local_read<uint32_t>(b+54925)!=10052||
           local_read<uint8_t>(b+54929)!=0x1d||local_read<uint32_t>(b+54930)!=0xc455cc19U||
           local_read<uint8_t>(b+54934)!=0x21||local_read<uint32_t>(b+54935)!=local_read<uint32_t>(f+24)||
           local_read<uint32_t>(b+54939)||local_read<uint32_t>(b+54943)||
           local_read<uint32_t>(b+54947)!=0x4d163017U)return false;
        const auto delay=local_read<uint64_t>(b+54897),latent=local_read<uint64_t>(b+54912);
        if(!exact_name(base,delay+24,"Delay")||
           !e33_mesh::named(base,local_read<uint64_t>(delay+32),"KismetSystemLibrary","/Script/Engine")||
           local_read<uint64_t>(delay+0xd8)!=base+0x3840d30||
           local_read<uint32_t>(delay+0xb0)!=0x4022403U||local_read<uint16_t>(delay+0xb6)!=40||
           !e33_mesh::named(base,latent,"LatentActionInfo","/Script/Engine"))return false;
        const auto again=local_read<Array>(f+0x60);
        if(std::memcmp(&script,&again,sizeof(script)))return false;
        at=b+54907;return true;
    }
};
