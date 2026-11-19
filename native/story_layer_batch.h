#pragma once
#include "enum_call_protocol.h"
#include "ui_batch_protocol.h"

// Exact scalar-only layer calls. Original reflected-call validation is supplied
// by Ops for every preflight and dispatch; this envelope grants no new calls.
namespace e33_story_layers {
constexpr uint32_t operation=264,limit=16,header=64,extent=20984;
constexpr uint32_t rejected=4330,stopped=4331,uncertain=4332;
inline bool same(const CallIdentity& a,const CallIdentity& b){return !std::memcmp(&a,&b,sizeof(a));}
inline bool identity(const CallIdentity& id){return id.index>=0&&id.serial>=0&&id.address>=0x10000&&id.address<=0x7fffffffffffULL&&!(id.address&7);}
inline const CallField* field(const CallPacket& p,const char* name){
    for(uint32_t i=0;i<p.field_count;++i)if(!std::strcmp(p.fields[i].name,name))return &p.fields[i];
    return nullptr;
}
inline uint32_t kind(const RetainedCallPacket& packet){
    if(validate_enum_call(packet)||retained_call_slots(packet.call))return 0;
    const auto& p=packet.call;
    const auto* layer=field(p,"InDataLayerInstance"),*result=field(p,"ReturnValue");
    if(!layer||!result||layer->kind!=CallObject||layer->flags&0x500||layer->dimension!=1||
       result->dimension!=1||!(result->flags&0x400)||p.object_count!=1||
       p.objects[0].offset!=layer->offset||!identity(p.objects[0].identity))return 0;
    if(p.field_count==2&&result->kind==kEnumCallKind)return 1;
    const auto* state=field(p,"InState"),*recursive=field(p,"bInIsRecursive");
    if(p.field_count!=4||!state||!recursive||state->kind!=kEnumCallKind||state->flags&0x500||
       state->dimension!=1||p.data[state->offset]>2||recursive->kind!=CallBool||recursive->flags&0x500||
       recursive->dimension!=1||p.data[recursive->offset]||result->kind!=CallBool)return 0;
    return 2;
}
inline bool item(const uint8_t* input,uint32_t size,uint32_t& at,RetainedCallPacket& out){
    if(at>size||size-at<4)return false;
    const auto n=e33_ui::word(input+at);at+=4;
    if(!n||n>size-at||!e33_ui::expand(input+at,n,&out,sizeof(out)))return false;
    at+=n;return true;
}
template<class Ops> void run(uint8_t* raw,size_t bytes,Ops& ops){
    if(bytes!=extent)return;
    uint8_t input[extent]{},output[extent]{};
    std::memcpy(input,raw,extent);std::memcpy(output,input,header);
    const auto count=e33_ui::word(input+48),size=e33_ui::word(input+52);
    uint32_t error=rejected,done=0,used=header,at=header,mode=0;
    CallIdentity world{},controller{},manager{};
    std::memcpy(&world,input+16,16);std::memcpy(&controller,input+32,16);
    bool valid=e33_ui::word(input)==3&&e33_ui::word(input+4)==operation&&
        !e33_ui::word(input+8)&&!e33_ui::word(input+12)&&!e33_ui::word(input+56)&&!e33_ui::word(input+60)&&
        count&&count<=limit&&size>=header&&size<=extent-limit*64&&identity(world)&&identity(controller);
    if(valid)for(uint32_t i=size;i<extent;++i)if(input[i]){valid=false;break;}
    RetainedCallPacket call{};
    // Validate the whole bounded request before changing even the first layer.
    for(uint32_t i=0;i<count&&valid;++i){
        valid=item(input,size,at,call);
        const auto current=valid?kind(call):0;
        if(!i){mode=current;manager=call.call.target;}
        valid=valid&&mode&&current==mode&&same(call.call.target,manager)&&ops.validate(world,controller,call,mode);
    }
    valid=valid&&at==size;
    if(valid){
        error=0;at=header;
        for(uint32_t i=0;i<count;++i){
            if(!item(input,size,at,call)){error=uncertain;break;}
            const auto layer=call.call.objects[0];
            // Context and full schema checks must run again at this point.
            ops.dispatch(world,controller,call,mode);
            uint32_t encoded=0;
            if(used+4>extent||!e33_ui::compress(&call,sizeof(call),output+used+4,extent-used-4,encoded)){
                error=uncertain;break;
            }
            e33_ui::put(output+used,encoded);used+=4+encoded;++done;
            const auto* result=field(call.call,"ReturnValue");
            if(call.count||call.call.object_count!=1||call.call.objects[0].offset!=layer.offset||
               !same(call.call.objects[0].identity,layer.identity)||call.call.error||call.call.outcome!=CallDispatchReturned||
               !result||(mode==1?call.call.data[result->offset]>2:call.call.data[result->offset]!=1)){
                error=call.call.outcome==CallOutcomeUnknown?uncertain:stopped;break;
            }
        }
    }
    e33_ui::put(output+8,error);e33_ui::put(output+12,done);e33_ui::put(output+52,used);
    std::memcpy(raw,output,extent);
}
}
