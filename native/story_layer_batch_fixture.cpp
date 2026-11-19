#include "story_layer_batch.h"
#include <cassert>
#include <vector>

using namespace e33_story_layers;
static RetainedCallPacket make(bool setter=false){
    RetainedCallPacket p{};auto& c=p.call;
    c.version=4;c.parameter_size=setter?11:9;c.allocation_extent=16;c.return_offset=setter?10:8;
    c.field_count=setter?4:2;c.object_count=1;c.target={1,1001,0x10000};c.function={2,1002,0x20000};
    c.fields[0]={CallObject,0,8,1,0x80,0,"InDataLayerInstance",{3,1003,0x30000}};
    c.objects[0]={0,{4,1004,0x40000}};
    if(setter){
        c.fields[1]={kEnumCallKind,8,1,1,0x80,0,"InState",{5,1005,0x50000}};
        c.fields[2]={CallBool,9,1,1,0x80,0xff010001,"bInIsRecursive",{}};
        c.fields[3]={CallBool,10,1,1,0x480,0xff010001,"ReturnValue",{}};c.data[8]=2;
    }else c.fields[1]={kEnumCallKind,8,1,1,0x480,0,"ReturnValue",{5,1005,0x50000}};
    assert(kind(p)==(setter?2U:1U));return p;
}
static std::vector<uint8_t> encode(const std::vector<RetainedCallPacket>& calls){
    std::vector<uint8_t> p(extent);e33_ui::put(p.data(),3);e33_ui::put(p.data()+4,operation);
    CallIdentity world{10,1010,0xa0000},pc{11,1011,0xb0000};
    std::memcpy(p.data()+16,&world,16);std::memcpy(p.data()+32,&pc,16);
    e33_ui::put(p.data()+48,static_cast<uint32_t>(calls.size()));uint32_t at=header;
    for(const auto& call:calls){uint32_t bytes=0;assert(e33_ui::compress(&call,sizeof(call),p.data()+at+4,extent-at-4,bytes));e33_ui::put(p.data()+at,bytes);at+=4+bytes;}
    e33_ui::put(p.data()+52,at);return p;
}
struct Ops {
    unsigned checked=0,dispatched=0;int fail_validation=-1,fail_dispatch=-1;bool unknown=false,reject_context=false;
    bool validate(const CallIdentity&,const CallIdentity&,RetainedCallPacket&,uint32_t){return int(checked++)!=fail_validation&&!reject_context;}
    void dispatch(const CallIdentity&,const CallIdentity&,RetainedCallPacket& p,uint32_t mode){
        const bool fail=int(dispatched++)==fail_dispatch;
        p.call.outcome=fail?(unknown?CallOutcomeUnknown:CallNotDispatched):CallDispatchReturned;
        p.call.error=fail?201U:0U;
        if(!fail)p.call.data[p.call.return_offset]=mode==1?2:1;
    }
};
int main(){
    {auto p=encode({make(),make(),make()});Ops ops;run(p.data(),p.size(),ops);assert(ops.checked==3&&ops.dispatched==3);assert(!e33_ui::word(p.data()+8)&&e33_ui::word(p.data()+12)==3);}
    {auto p=encode({make(true),make(true),make(true)});Ops ops;ops.fail_validation=2;run(p.data(),p.size(),ops);assert(ops.dispatched==0&&e33_ui::word(p.data()+8)==rejected&&!e33_ui::word(p.data()+12));}
    {auto p=encode({make(),make(true)});Ops ops;run(p.data(),p.size(),ops);assert(!ops.dispatched&&e33_ui::word(p.data()+8)==rejected);}
    {auto bad=make();std::memset(bad.call.fields[0].name,0,96);std::memcpy(bad.call.fields[0].name,"AnythingElse",13);auto p=encode({bad});Ops ops;run(p.data(),p.size(),ops);assert(!ops.dispatched&&e33_ui::word(p.data()+8)==rejected);}
    {auto bad=make(true);bad.call.data[9]=1;auto p=encode({bad});Ops ops;run(p.data(),p.size(),ops);assert(!ops.dispatched&&e33_ui::word(p.data()+8)==rejected);}
    for(bool uncertain_outcome:{false,true}){auto p=encode({make(true),make(true),make(true)});Ops ops;ops.fail_dispatch=1;ops.unknown=uncertain_outcome;run(p.data(),p.size(),ops);
        assert(ops.dispatched==2&&e33_ui::word(p.data()+12)==2);assert(e33_ui::word(p.data()+8)==(uncertain_outcome?uncertain:stopped));
        uint32_t at=header;RetainedCallPacket first{},second{};assert(item(p.data(),e33_ui::word(p.data()+52),at,first)&&item(p.data(),e33_ui::word(p.data()+52),at,second));
        assert(first.call.outcome==CallDispatchReturned&&second.call.error==201);}
    {auto p=encode({make()});p.back()=1;Ops ops;run(p.data(),p.size(),ops);assert(!ops.checked&&!ops.dispatched);}
    {auto p=encode(std::vector<RetainedCallPacket>(17,make()));Ops ops;run(p.data(),p.size(),ops);assert(!ops.checked&&!ops.dispatched);}
    {auto p=encode({make()});Ops ops;ops.reject_context=true;run(p.data(),p.size(),ops);assert(!ops.dispatched);}
}
