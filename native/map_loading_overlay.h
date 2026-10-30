#pragma once
#include "engine_profiles.h"

// Python retains the entire process-owned tree. This helper only borrows its
// exact positive identities while the loading gate owns presentation. It never
// activates CommonUI or changes focus/input mode.
namespace e33_map_loading_overlay {
using namespace e33_mesh;
class Cover {
    CallIdentity ids_[5]{};
    bool configured_=false,visible_=false;
    const MeshFunction& profile(unsigned i)const{
        static const MeshField order[]={{"ZOrder","IntProperty",0,4,6759867280786048ULL,0x6e10a98ULL,"","",0,"",0U,""}};
        static const MeshFunction add={"UserWidget","AddToViewport",67240971,4,4,65535,0x31355b0,order,1};
        static const MeshField result[]={{"ReturnValue","BoolProperty",0,1,0x18001040000780ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
        static const MeshFunction attached={"Widget","IsInViewport",0x5402040b,1,1,0,0x31008b0,result,1};
        return i==1?e33_engine_profiles::profiles[28]:i==2?add:i==3?attached:e33_engine_profiles::profiles[30];
    }
    bool schema(uint64_t b,unsigned i)const{
        if(i<1||i>4||!TargetPodSchemaOps{b}.context())return false;
        const auto fn=call_identity(b,ids_[i]),object=call_identity(b,ids_[0]);
        const auto&p=profile(i);
        if(!fn||!object||!exact_name(b,local_read<uint64_t>(fn+16)+24,"Function")||
           !named(b,local_read<uint64_t>(fn+32),p.owner,"/Script/UMG")||
           !exact_name(b,fn+24,p.name)||local_read<uint32_t>(fn+0xb0)!=p.flags||
           local_read<uint16_t>(fn+0xb6)!=p.params||local_read<uint16_t>(fn+0xb8)!=p.returned||
           local_read<int32_t>(fn+0x58)!=int(p.extent)||local_read<uint64_t>(fn+0xd8)!=b+p.entry||
           !fields(b,fn,p.fields,p.count)||
           !call_derives(b,local_read<uint64_t>(object+16),local_read<uint64_t>(fn+32)))return false;
        if(local_read<uint32_t>(object+8)&0x40018030U)return false;
        const auto pe=local_read<uint64_t>(local_read<uint64_t>(object)+0x268);
        return pe==b+0x1393330||pe==b+0x332bb90;
    }
    bool call(uint64_t b,unsigned i,void*args)const{
        if(!schema(b,i))return false;
        const auto object=call_identity(b,ids_[0]),fn=call_identity(b,ids_[i]);
        const auto pe=local_read<uint64_t>(local_read<uint64_t>(object)+0x268);
        reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(pe)(
            reinterpret_cast<void*>(object),reinterpret_cast<void*>(fn),args);
        return true;
    }
public:
    bool configured()const{return configured_;}
    bool visible()const{return visible_;}
    bool configure(uint64_t b,const CallIdentity*ids){
        if(configured_||!ids)return false;
        for(unsigned i=0;i<5;++i)if(ids[i].index<0||ids[i].serial<=0||!ids[i].address)return false;
        std::memcpy(ids_,ids,sizeof(ids_));
        for(unsigned i=1;i<5;++i)if(!schema(b,i)){std::memset(ids_,0,sizeof(ids_));return false;}
        configured_=true;return true;
    }
    bool show(uint64_t b){
        if(!configured_)return false;
        // Travel can call RemoveAllWidgets. Check actual membership each time;
        // never trust our previous AddToViewport acknowledgement as proof.
        uint8_t attached=0;if(!call(b,3,&attached)||attached>1)return false;
        if(attached&&visible_)return true;
        if(!attached){int32_t order=10000;if(!call(b,2,&order))return false;
            attached=0;if(!call(b,3,&attached)||attached!=1)return false;}
        uint8_t visibility=3; // ESlateVisibility::HitTestInvisible, target profile.
        if(!call(b,1,&visibility))return false;
        visible_=true;return true;
    }
    bool hide(uint64_t b){
        if(!configured_)return true;
        if(!visible_)return true;
        if(!visible_)return true;
        uint8_t visibility=1; // ESlateVisibility::Collapsed, target profile.
        if(!call(b,1,&visibility))return false;
        visible_=false;return true;
    }
    bool detach(uint64_t b){
        if(!configured_)return true;
        if(!call_identity(b,ids_[0])){
            // A purged identity cannot own a live viewport widget. Never invoke
            // a replacement object that has recycled its old registry slot.
            configured_=visible_=false;std::memset(ids_,0,sizeof(ids_));return true;
        }
        if(!hide(b)||!call(b,4,nullptr))return false;
        uint8_t attached=0;if(!call(b,3,&attached)||attached)return false;
        configured_=visible_=false;std::memset(ids_,0,sizeof(ids_));return true;
    }
};
}
