#pragma once
#include "mesh_owner.h"
#include "picto_progression.h"
namespace e33_battle_state {
struct Observation {
    bool started=false,finishing=false;int enemy_count=0;
    uint64_t arena=0,encounter_name=0;
    bool idle()const{return !started&&!finishing&&!enemy_count&&!arena&&!encounter_name;}
};
// Original enemy-helper readback, shared without changing accepted bounds or
// idle semantics. Caller establishes exact current manager/controller ownership.
inline bool observe(uint64_t base,uint64_t manager,Observation& output){
    const auto initialized=picto_field(base,manager,"IsBattleInitialized","BoolProperty",168,1);
    const auto ending=picto_field(base,manager,"HasBattleStartedEndFlow","BoolProperty",1961,1);
    const auto enemies=picto_field(base,manager,"Enemies","ArrayProperty",200,16);
    const auto arena=picto_field(base,manager,"BattleMapBP","ObjectProperty",728,8);
    uint64_t descriptor=0;
    const auto parameters=picto_field(base,manager,"CurrentBattleStartParams","StructProperty",1224,344,&descriptor);
    if(!initialized||!ending||!enemies||!arena||!parameters||!descriptor||
       !e33_mesh::named(base,local_read<uint64_t>(descriptor+0x70),"FBattleStartParams","/Game/Gameplay/Battle/FBattleStartParams"))return false;
    const auto count=local_read<int32_t>(enemies+8),capacity=local_read<int32_t>(enemies+12);
    const auto started=local_read<uint8_t>(initialized),finishing=local_read<uint8_t>(ending);
    if(started>1||finishing>1||count<0||count>1024||capacity<count||capacity>4096)return false;
    output={started!=0,finishing!=0,count,local_read<uint64_t>(arena),local_read<uint64_t>(parameters+16)};
    return true;
}
}
