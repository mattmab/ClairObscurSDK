#pragma once
#include "mesh_owner.h"
#include "picto_progression.h"
namespace e33_npc_presentation {
struct RegisteredInterface {uint64_t object=0,interface_pointer=0;};
struct MembershipObservation {
    uint32_t totals[5]{},owned[5]{};
    RegisteredInterface owned_interface{};
    bool absent()const{for(const auto count:owned)if(count)return false;return true;}
};
// Game-thread counterpart of the retained read-only membership diagnostic.
// The same five exact schemas/bounds are checked. No registry is cleared and no
// reference to another actor is modified. Invalid reads are never "absence".
inline bool observe_memberships(uint64_t b,CallIdentity system,CallIdentity controller,
        CallIdentity actor,MembershipObservation& out){
    out={};
    if(!TargetPodSchemaOps{b}.context()||actor.index<0||actor.serial<=0||actor.address<0x10000||
       !call_identity(b,system)||!call_identity(b,controller)||!call_identity(b,actor)||
       !e33_mesh::named(b,local_read<uint64_t>(system.address+16),"BP_InteractionSystem_C",
           "/Game/Gameplay/Exploration/BP_InteractionSystem")||
       local_read<uint64_t>(system.address+32)!=controller.address||(local_read<uint32_t>(system.address+8)&0x30))return false;
    const auto cls=local_read<uint64_t>(system.address+16);
    auto property=[&](const char* name,const char* type,int offset,int width,uint64_t table){
        uint64_t found=0;unsigned walked=0;
        for(auto f=local_read<uint64_t>(cls+0x50);f&&++walked<=128;f=local_read<uint64_t>(f+24)){
            if(!exact_name(b,f+32,name))continue;
            if(found||local_read<uint64_t>(f)!=b+table||local_read<uint64_t>(f+16)!=(cls|1)||
               !exact_name(b,local_read<uint64_t>(f+8),type)||local_read<int32_t>(f+0x30)!=1||
               local_read<int32_t>(f+0x34)!=width||local_read<int32_t>(f+0x44)!=offset)return uint64_t(0);
            found=f;
        }
        return walked<=128?found:uint64_t(0);
    };
    if(!property("ParentControllerWorld","ObjectProperty",416,8,0x6e11d38)||
       local_read<uint64_t>(system.address+416)!=controller.address)return false;
    auto interface_value=[&](uint64_t at,unsigned group){
        RegisteredInterface value{local_read<uint64_t>(at),local_read<uint64_t>(at+8)};
        if(!value.object)return !value.interface_pointer;
        const auto observed=call_capture(b,value.object);
        if(!observed.address)return false;
        ++out.totals[group];
        if(observed.index==actor.index||value.object==actor.address){
            if(observed.index!=actor.index||observed.serial!=actor.serial||value.object!=actor.address)return false;
            if(out.owned_interface.object&&out.owned_interface.interface_pointer!=value.interface_pointer)return false;
            out.owned_interface=value;++out.owned[group];
            if(group<2&&out.owned[group]>1)return false;
        }
        return true;
    };
    for(unsigned group=0;group<2;++group){
        const int offset=group?184:168;
        const auto field=property(group?"DistantInteractiveObjects":"InteractiveObjects","ArrayProperty",offset,16,0x6e0de80);
        if(!field||(local_read<uint8_t>(field+0x70)&1))return false;
        const auto inner=local_read<uint64_t>(field+0x78);
        if(!inner||local_read<uint64_t>(inner)!=b+0x6e12ea8||local_read<uint64_t>(inner+16)!=field||
           local_read<int32_t>(inner+0x30)!=1||local_read<int32_t>(inner+0x34)!=16)return false;
        const auto at=system.address+offset,data=local_read<uint64_t>(at);
        const auto count=local_read<int32_t>(at+8),capacity=local_read<int32_t>(at+12);
        if(count<0||capacity<count||capacity>8192||(count&&(data<0x10000||(data&7))))return false;
        for(int i=0;i<count;++i)if(!interface_value(data+uint64_t(i)*16,group))return false;
    }
    for(unsigned group=3;group<5;++group){
        const int offset=group==3?200:232;
        if(!property(group==3?"ActiveInteraction":"2DInteraction","InterfaceProperty",offset,16,0x6e12ea8)||
           !interface_value(system.address+offset,group))return false;
    }
    const auto field=property("DisplayedDistantInteractiveObjects","MapProperty",304,80,0x6e13370);
    if(!field)return false;
    const auto key=local_read<uint64_t>(field+0x70),value=local_read<uint64_t>(field+0x78);
    if(!key||!value||local_read<uint64_t>(key)!=b+0x6e136a0||local_read<uint64_t>(value)!=b+0x6e12ea8||
       local_read<uint64_t>(key+16)!=field||local_read<uint64_t>(value+16)!=field||
       local_read<int32_t>(key+0x34)!=16||local_read<int32_t>(key+0x44)!=0||
       local_read<int32_t>(value+0x34)!=16||local_read<int32_t>(value+0x44)!=16||
       !exact_name(b,local_read<uint64_t>(key+0x70)+24,"FPromptID"))return false;
    const auto stride=local_read<int32_t>(field+0x8c);
    if(stride<32||stride>64||local_read<int32_t>(field+0x80)!=16||(local_read<uint8_t>(field+0x98)&1))return false;
    const auto map=system.address+304,data=local_read<uint64_t>(map),heap=local_read<uint64_t>(map+32),masks=heap?heap:map+16;
    const auto count=local_read<int32_t>(map+8),capacity=local_read<int32_t>(map+12),bits=local_read<int32_t>(map+40),
        bitcapacity=local_read<int32_t>(map+44),free=local_read<int32_t>(map+52);
    if(count<0||count>capacity||capacity>8192||bits!=count||bitcapacity<bits||bitcapacity>8192||free<0||free>count||
       (!heap&&bitcapacity>128)||(count&&(data<0x10000||(data&7))))return false;
    int live=0;
    for(int i=0;i<count;++i){
        if(!(local_read<uint32_t>(masks+uint64_t(i/32)*4)&(1U<<(i%32))))continue;
        ++live;if(!interface_value(data+uint64_t(i)*stride+16,2))return false;
    }
    return live==count-free&&call_identity(b,system)&&call_identity(b,controller)&&
        local_read<uint64_t>(system.address+416)==controller.address;
}
}
