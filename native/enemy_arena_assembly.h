#pragma once
#include "enemy_arena_slots.h"
#include <cmath>
#include <cstring>
namespace e33_enemy_spawn {
struct ArenaAssemblyObservation {
    uint64_t enemy_mask=0,party_mask=0;
    uint32_t slots=0,streaming_enabled=0,transform_components=0,reserved=0;
};
static_assert(sizeof(ArenaAssemblyObservation)==32,"arena observation wire extent");
inline bool arena_live(uint64_t b,uint64_t object){
    return object>=0x10000 && !(object&7) && call_capture(b,object).address==object &&
        !(local_read<uint32_t>(object+8)&0x40018030U);
}
inline bool arena_class(uint64_t b,uint64_t object,const char* name,const char* package){
    if(!arena_live(b,object))return false;
    auto cls=local_read<uint64_t>(object+16);
    for(unsigned i=0;cls&&i<64;++i,cls=local_read<uint64_t>(cls+0x40)){
        if(!call_capture(b,cls).address)return false;
        if(exact_name(b,cls+24,name)&&exact_name(b,local_read<uint64_t>(cls+32)+24,package))return true;
    }
    return false;
}
inline bool arena_world(uint64_t b,uint64_t object,uint64_t world){
    for(unsigned i=0;object&&i<64;++i,object=local_read<uint64_t>(object+32)){
        if(!call_capture(b,object).address)return false;
        if(object==world)return true;
    }
    return false;
}
inline uint64_t arena_reference(uint64_t b,uint64_t object,const char* name,int offset){
    const auto storage=picto_field(b,object,name,"ObjectProperty",offset,8);
    const auto value=storage?local_read<uint64_t>(storage):0;
    return arena_live(b,value)?value:0;
}
inline bool arena_scene(uint64_t b,uint64_t object,uint64_t owner){
    if(!arena_class(b,object,"SceneComponent","/Script/Engine")||local_read<uint64_t>(object+32)!=owner)return false;
    const char* names[]={"RelativeLocation","RelativeRotation","RelativeScale3D"};
    const char* types[]={"Vector","Rotator","Vector"};
    for(unsigned i=0;i<3;++i){
        uint64_t descriptor=0;
        const auto value=picto_field(b,object,names[i],"StructProperty",296+int(i)*24,24,&descriptor);
        const auto structure=descriptor?local_read<uint64_t>(descriptor+0x70):0;
        if(!value||!structure||!exact_name(b,structure+24,types[i])||
           !exact_name(b,local_read<uint64_t>(structure+32)+24,"/Script/CoreUObject")||local_read<int32_t>(structure+0x58)!=24)return false;
        for(unsigned j=0;j<3;++j){
            const auto scalar=local_read<double>(value+j*8);
            if(!std::isfinite(scalar)||std::abs(scalar)>1.e8||(i==2&&std::abs(scalar)<1.e-9))return false;
        }
    }
    return true;
}
// Current original arena pattern: seven declared spawn components. This is a
// structural observation, not a streaming-completion or battle-readiness claim.
inline uint32_t observe_arena_assembly(uint64_t b,uint64_t world,uint64_t arena,ArenaAssemblyObservation& output){
    output={};
    if(!arena_class(b,arena,"BP_BattleMap_C","/Game/Levels/Battle_Maps/BP_BattleMap")||!arena_world(b,arena,world))return 2942;
    const auto source=arena_reference(b,arena,"WorldPartitionStreamingSource",672);
    uint64_t descriptor=0;
    const auto enabled=source?picto_field(b,source,"bStreamingSourceEnabled","BoolProperty",249,1,&descriptor):0;
    if(!arena_class(b,source,"WorldPartitionStreamingSourceComponent","/Script/Engine")||
       local_read<uint64_t>(source+32)!=arena||!enabled||!descriptor||local_read<uint32_t>(descriptor+0x70)!=0xff010001U)return 2943;
    output.streaming_enabled=local_read<uint8_t>(enabled);
    if(output.streaming_enabled>1)return 2943;
    struct Slot {const char* name;int offset;bool enemy;};
    static const Slot slots[]={
        {"BP_jRPG_EnemyBattleSpot0",792,true},{"BP_jRPG_EnemyBattleSpot3",824,true},
        {"BP_jRPG_EnemyBattleSpot2",832,true},{"BP_jRPG_EnemyBattleSpot1",840,true},
        {"BP_jRPG_CharacterBattleSpot2",848,false},{"BP_jRPG_CharacterBattleSpot1",856,false},
        {"BP_jRPG_CharacterBattleSpot",864,false}};
    ArenaSlotEvidence evidence[7]{};
    for(unsigned i=0;i<7;++i){
        const auto& slot=slots[i];
        const auto component=arena_reference(b,arena,slot.name,slot.offset);
        if(!arena_class(b,component,"ChildActorComponent","/Script/Engine")||local_read<uint64_t>(component+32)!=arena)return 2944;
        const auto child=arena_reference(b,component,"ChildActor",568);
        if(!arena_class(b,child,slot.enemy?"BP_jRPG_EnemyBattleSpot_C":"BP_jRPG_CharacterBattleSpot_C",
            slot.enemy?"/Game/jRPGTemplate/Blueprints/Other/Battle/BP_jRPG_EnemyBattleSpot":"/Game/jRPGTemplate/Blueprints/Other/Battle/BP_jRPG_CharacterBattleSpot")||!arena_world(b,child,world))return 2945;
        const auto index=picto_field(b,child,"SlotIndex","IntProperty",slot.enemy?712:736,4);
        if(!index)return 2945;
        const auto position=arena_reference(b,child,"SpawnPosition",664);
        const auto front=arena_reference(b,child,slot.enemy?"Arrow":"FrontlineArrow",slot.enemy?688:712);
        const auto back=slot.enemy?0:arena_reference(b,child,"BacklineArrow",688);
        evidence[i]={local_read<int32_t>(index),slot.enemy,true,arena_scene(b,position,child),
                     arena_scene(b,front,child),slot.enemy||arena_scene(b,back,child)};
        if(evidence[i].position_valid)++output.transform_components;
        if(evidence[i].front_arrow_valid)++output.transform_components;
        if(!slot.enemy&&evidence[i].back_arrow_valid)++output.transform_components;
    }
    const auto validation=validate_arena_slots(evidence,7,0,0,true);
    if(validation.result!=ArenaSlotsResult::Ok)return 2946;
    output.enemy_mask=validation.enemy_mask;output.party_mask=validation.party_mask;output.slots=7;
    return 0;
}
}
