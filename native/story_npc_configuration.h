#pragma once
#include "invocation_protocol.h"
namespace e33_story_npc {
constexpr uint32_t operation=230,rejected=3870,unknown=3871;
#pragma pack(push,1)
struct Packet {
    uint32_t version=3,op=operation,error=0,state=0;uint64_t owner=0;
    CallIdentity npc{},dialogue_class{},speaker{},system_cdo{},definitions[4]{};
    uint32_t activate=0;uint8_t tail[20828]{};
};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984,"Story NPC configuration packet");
inline bool identity(const CallIdentity& id){return id.index>=0&&id.serial>=0&&id.address>=0x10000&&id.address<=0x7fffffffffffULL&&!(id.address&7);}
inline bool valid(const Packet& p){
    if(p.version!=3||p.op!=operation||p.error||p.state||!p.owner||p.activate>1||
       !identity(p.npc)||!identity(p.dialogue_class)||!identity(p.speaker)||!identity(p.system_cdo))return false;
    for(const auto& id:p.definitions)if(!identity(id))return false;
    for(auto b:p.tail)if(b)return false;
    return true;
}
struct Journal {bool configure_attempted=false,configured=false,activate_attempted=false,active=false;};
template<class Ops> uint32_t configure(Journal& journal,bool activate,Ops& ops,bool collision_enabled=true,bool validate_only=false){
    if(!ops.preflight())return rejected;
    if(activate){
        if(!journal.configured||journal.activate_attempted||!ops.matches())return rejected;
        if(validate_only)return 0;
        journal.activate_attempted=true;
        if(!ops.interactable(true)||!ops.collision(collision_enabled))return unknown;
        journal.active=true;return 0;
    }
    if(journal.configure_attempted||validate_only)return rejected;
    journal.configure_attempted=true;
    if(!ops.interactable(false)||!ops.dialogue()||!ops.speaker()||!ops.matches())return unknown;
    journal.configured=true;return 0;
}
}
