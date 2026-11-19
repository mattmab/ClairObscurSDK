#include "story_world_configuration.h"
#include <cassert>
#include <vector>
using namespace e33_story_world;
static Header make_header(bool wall,bool mesh=false){
    Header h{};h.owner=99;h.kind=wall?1:2;h.count=mesh?7:6;h.mobility=0;
    h.world={10,1010,0xa0000};h.controller={11,1011,0xb0000};h.actor={12,1012,0xc0000};h.root={13,1013,0xd0000};
    if(wall)h.mesh={14,1014,0xe0000};return h;
}
static RetainedCallPacket make(const Header&h,uint32_t i){
    RetainedCallPacket p{};auto&c=p.call;const auto s=step(h,i);
    c.version=1;c.parameter_size=1;c.allocation_extent=8;c.return_offset=65535;c.field_count=1;
    c.target=(s==Movable||s==RestoreMobility)?h.root:s==MeshScale?h.mesh:h.actor;c.function={20+int(i),1020+int(i),0x140000+0x10000*i};
    if(s==Movable||s==RestoreMobility){c.fields[0]={CallByte,0,1,1,0x80,0,"NewMobility",{}};c.data[0]=s==Movable?2:uint8_t(h.mobility);}
    else if(s==ActorScale||s==MeshScale){
        c.version=2;c.parameter_size=24;c.allocation_extent=24;c.fields[0]={CallVector,0,24,1,0x80,0,"NewScale3D",{30,1030,0x1e0000}};
        double values[3]={1.,2.,3.};std::memcpy(c.data,values,24);
    }else{
        c.fields[0]={CallBool,0,1,1,0x80,0xff010001,"",{}};
        const auto name=s==WallEnabled?"Enabled":s==Collision?"bNewActorEnableCollision":s==Hidden?"bNewHidden":"bEnabled";
        std::memcpy(c.fields[0].name,name,std::strlen(name)+1);c.data[0]=h.kind==1&&(s==Collision||s==Hidden)?1:0;
        if(s==WallEnabled){c.version=8;c.entry_rva=kBlueprintThunkRva;}
    }
    assert(shape(h,i,p));return p;
}
static std::vector<RetainedCallPacket> calls(const Header&h){
    std::vector<RetainedCallPacket> out;for(uint32_t i=0;i<h.count;++i)out.push_back(make(h,i));return out;
}
static std::vector<uint8_t> encode(Header h,const std::vector<RetainedCallPacket>&items){
    std::vector<uint8_t> out(extent);uint32_t at=header;
    for(const auto&p:items){uint32_t n=0;assert(e33_ui::compress(&p,sizeof(p),out.data()+at+4,extent-at-4,n));e33_ui::put(out.data()+at,n);at+=4+n;}
    h.size=at;std::memcpy(out.data(),&h,header);return out;
}
struct Ops{
    unsigned checked=0,dispatched=0;int reject_at=-1,fail_at=-1;bool unknown=false;
    bool validate(const Header&,uint32_t,RetainedCallPacket&){return int(checked++)!=reject_at;}
    void dispatch(const Header&,uint32_t,RetainedCallPacket&p){
        const bool fail=int(dispatched++)==fail_at;p.call.outcome=fail?(unknown?CallOutcomeUnknown:CallNotDispatched):CallDispatchReturned;p.call.error=fail?201:0;
    }
};
int main(){
    for(const auto h:{make_header(false),make_header(true),make_header(true,true)}){
        auto original=encode(h,calls(h)),data=original;Journal journal;Ops ops;run(data.data(),data.size(),journal,ops);
        assert(journal.attempted&&journal.complete&&journal.completed==h.count&&ops.checked==h.count&&ops.dispatched==h.count);
        assert(!e33_ui::word(data.data()+8)&&e33_ui::word(data.data()+12)==h.count);
        auto replay=original;run(replay.data(),replay.size(),journal,ops);assert(ops.dispatched==h.count&&e33_ui::word(replay.data()+8)==rejected);
        for(uint32_t i=0;i<h.count;++i){auto packet=original;Journal j;Ops o;o.reject_at=int(i);run(packet.data(),packet.size(),j,o);assert(!j.attempted&&!o.dispatched&&e33_ui::word(packet.data()+8)==rejected);}
        for(bool unknown:{false,true}){auto packet=original;Journal j;Ops o;o.fail_at=2;o.unknown=unknown;run(packet.data(),packet.size(),j,o);
            assert(j.attempted&&!j.complete&&j.completed==3&&o.dispatched==3&&e33_ui::word(packet.data()+8)==(unknown?uncertain:stopped));}
    }
    auto h=make_header(true,true);
    for(int fault=0;fault<7;++fault){auto items=calls(h);auto changed=h;
        if(fault==0)items[0].call.target=h.actor;
        if(fault==1)items[3].call.data[0]=1;
        if(fault==2)items[4].call.data[0]=0;
        if(fault==3)items[6].call.data[0]=2;
        if(fault==4)items[1].count=1;
        if(fault==5)items[1].call.fields[0].flags|=0x100;
        if(fault==6)changed.kind=2;
        auto packet=encode(changed,items);Journal j;Ops o;run(packet.data(),packet.size(),j,o);assert(!j.attempted&&!o.dispatched&&e33_ui::word(packet.data()+8)==rejected);
    }
    {auto packet=encode(h,calls(h));packet.back()=1;Journal j;Ops o;run(packet.data(),packet.size(),j,o);assert(!o.checked&&!j.attempted);}
}
