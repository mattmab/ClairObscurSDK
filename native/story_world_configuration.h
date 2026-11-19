#pragma once
#include "retained_call_protocol.h"
#include "blueprint_call_protocol.h"
#include "ui_batch_protocol.h"
#include <cmath>

namespace e33_story_world {
constexpr uint32_t operation=266,extent=20984,header=128,limit=7;
constexpr uint32_t rejected=4350,stopped=4351,uncertain=4352;
#pragma pack(push,1)
struct Header {
    uint32_t version=3,operation_id=operation,error=0,completed=0;
    uint64_t owner=0;uint32_t kind=0,count=0,size=0,reserved=0;
    CallIdentity world{},controller{},actor{},root{},mesh{};
    uint32_t mobility=0,reserved2=0;
};
#pragma pack(pop)
static_assert(sizeof(Header)==header);
struct Journal {bool attempted=false,complete=false;uint32_t completed=0;};
enum Step:uint32_t {Movable,ActorScale,MeshScale,WallEnabled,Collision,Hidden,Tick,RestoreMobility};
inline bool same(const CallIdentity&a,const CallIdentity&b){return !std::memcmp(&a,&b,sizeof(a));}
inline bool identity(const CallIdentity&id){return id.index>=0&&id.serial>=0&&id.address>=0x10000&&id.address<=0x7fffffffffffULL&&!(id.address&7);}
inline bool empty(const CallIdentity&id){return !id.index&&!id.serial&&!id.address;}
inline Step step(const Header&h,uint32_t i){
    if(i==0)return Movable;if(i==1)return ActorScale;if(i+1==h.count)return RestoreMobility;
    if(h.kind==2)return i==2?Tick:i==3?Collision:Hidden;
    if(h.count==7&&i==2)return MeshScale;
    const auto n=i-(h.count==7?1U:0U);return n==2?WallEnabled:n==3?Collision:Hidden;
}
inline const char* function(Step s){
    switch(s){case Movable:case RestoreMobility:return "SetMobility";case ActorScale:return "SetActorScale3D";
    case MeshScale:return "SetRelativeScale3D";case WallEnabled:return "SetInvisibleWallEnabled";
    case Collision:return "SetActorEnableCollision";case Hidden:return "SetActorHiddenInGame";case Tick:return "SetActorTickEnabled";}
    return "";
}
inline bool shape(const Header&h,uint32_t i,const RetainedCallPacket&p){
    const auto&c=p.call;const auto s=step(h,i);
    if(!retained_call_empty(p)||c.object_count||c.field_count!=1||c.return_offset!=65535||
       (s==WallEnabled?validate_blueprint_call(c):validate_call_packet(c,true)))return false;
    if(s!=WallEnabled&&c.version!=1&&c.version!=2)return false;
    const auto&f=c.fields[0];if(f.flags&0x500||!(f.flags&0x80)||f.dimension!=1)return false;
    const auto&expected_target=(s==Movable||s==RestoreMobility)?h.root:s==MeshScale?h.mesh:h.actor;
    if(!same(c.target,expected_target))return false;
    if(s==Movable||s==RestoreMobility)return f.kind==CallByte&&!std::strcmp(f.name,"NewMobility")&&c.data[f.offset]==(s==Movable?2U:h.mobility);
    if(s==ActorScale||s==MeshScale){
        if(f.kind!=15||f.width!=24||std::strcmp(f.name,"NewScale3D"))return false;
        double values[3]{};std::memcpy(values,c.data+f.offset,24);
        for(double v:values)if(!std::isfinite(v)||std::abs(v)>10000)return false;
        return true;
    }
    const auto name=s==WallEnabled?"Enabled":s==Collision?"bNewActorEnableCollision":s==Hidden?"bNewHidden":"bEnabled";
    const bool wanted=h.kind==1&&(s==Collision||s==Hidden);
    return f.kind==CallBool&&!std::strcmp(f.name,name)&&c.data[f.offset]==static_cast<uint8_t>(wanted);
}
inline bool item(const uint8_t*data,uint32_t size,uint32_t&at,RetainedCallPacket&call){
    if(at>size||size-at<4)return false;const auto n=e33_ui::word(data+at);at+=4;
    if(!n||n>size-at||!e33_ui::expand(data+at,n,&call,sizeof(call)))return false;at+=n;return true;
}
template<class Ops>void run(uint8_t*raw,size_t bytes,Journal&journal,Ops&ops){
    if(bytes!=extent)return;
    uint8_t input[extent]{},output[extent]{};std::memcpy(input,raw,extent);std::memcpy(output,input,header);
    Header h{};std::memcpy(&h,input,header);uint32_t error=rejected,done=0,used=header,at=header;
    bool valid=h.version==3&&h.operation_id==operation&&!h.error&&!h.completed&&h.owner&&!h.reserved&&!h.reserved2&&
        (h.kind==1||h.kind==2)&&(h.count==6||(h.kind==1&&h.count==7))&&h.size>=header&&h.size<=extent-limit*64&&h.mobility<=2&&
        identity(h.world)&&identity(h.controller)&&identity(h.actor)&&identity(h.root)&&
        (h.kind==1?identity(h.mesh):empty(h.mesh))&&!journal.attempted;
    if(valid)for(uint32_t i=h.size;i<extent;++i)if(input[i]){valid=false;break;}
    RetainedCallPacket call{};
    for(uint32_t i=0;i<h.count&&valid;++i)valid=item(input,h.size,at,call)&&shape(h,i,call)&&ops.validate(h,i,call);
    valid=valid&&at==h.size;
    if(valid){
        journal.attempted=true;error=0;at=header;
        for(uint32_t i=0;i<h.count;++i){
            if(!item(input,h.size,at,call)){error=uncertain;break;}
            ops.dispatch(h,i,call);
            uint32_t n=0;
            if(used+4>extent||!e33_ui::compress(&call,sizeof(call),output+used+4,extent-used-4,n)){error=uncertain;break;}
            e33_ui::put(output+used,n);used+=4+n;++done;journal.completed=done;
            if(call.count||call.call.object_count||call.call.error||call.call.outcome!=CallDispatchReturned){
                error=call.call.outcome==CallOutcomeUnknown?uncertain:stopped;break;
            }
        }
        journal.complete=!error&&done==h.count;
    }
    e33_ui::put(output+8,error);e33_ui::put(output+12,done);e33_ui::put(output+32,used);
    std::memcpy(raw,output,extent);
}
}
