#pragma once
#include "story_npc_configuration.h"
#include <initializer_list>

namespace e33_story_npc_finalize {
constexpr uint32_t operation=265,rejected=4340,uncertain=4341;
#pragma pack(push,1)
struct Packet {
    uint32_t version=3,op=operation,error=0,state=0;uint64_t owner=0;
    CallIdentity npc{},dialogue_class{},speaker{},system_cdo{},definitions[4]{};
    uint32_t interaction=0,show_visual=0;uint64_t visual_owner=0;CallIdentity visual{};
    uint32_t completed=0,attempted=0;uint8_t tail[20792]{};
};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984);
inline bool valid(const Packet& p){
    if(p.version!=3||p.op!=operation||p.error||p.state||!p.owner||p.interaction>1||p.show_visual>1||p.completed||p.attempted)return false;
    for(const auto& id:{p.npc,p.dialogue_class,p.speaker,p.system_cdo,p.definitions[0],p.definitions[1],p.definitions[2],p.definitions[3]})
        if(!e33_story_npc::identity(id))return false;
    if(p.show_visual){if(!p.visual_owner||p.visual_owner==p.owner||!e33_story_npc::identity(p.visual))return false;}
    else if(p.visual_owner||p.visual.index||p.visual.serial||p.visual.address)return false;
    for(auto b:p.tail)if(b)return false;
    return true;
}
struct Journal {bool attempted=false;uint32_t completed=0,steps_attempted=0;};
struct Result {uint32_t error=0,completed=0,attempted=0;};
template<class Ops> Result run(Journal& journal,bool visual,Ops& ops){
    Result result{};
    if(journal.attempted||!ops.validate()){result.error=rejected;return result;}
    journal.attempted=true;
    for(uint32_t step=1;step<=4;step<<=1){
        if(step==2&&!visual)continue;
        if(!ops.current()){result.error=uncertain;return result;}
        result.attempted|=step;
        journal.steps_attempted=result.attempted;
        if(!ops.perform(step)){result.error=uncertain;return result;}
        result.completed|=step;
        journal.completed=result.completed;
    }
    if(!ops.verify())result.error=uncertain;
    return result;
}
}
