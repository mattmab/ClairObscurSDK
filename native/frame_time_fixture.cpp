#include "pod_schema.h"
#include <map>
#include <string>
#include <stdexcept>
#include <iostream>

// Synthetic memory exercises the actual schema walker, including target offsets.
// It never attaches to a game or substitutes for subsequent live validation.
struct Memory {
    uint64_t base=0x140000000ULL, next=0x10000;
    std::map<uint64_t,uint64_t> words;
    std::map<uint64_t,std::string> names;
    std::map<uint64_t,CallIdentity> objects;
    bool live=true;
    unsigned context_calls=0, stop_after=100;
    bool context() { return live && ++context_calls<=stop_after; }
    template<class T> T read(uint64_t at) { return static_cast<T>(words.at(at)); }
    bool name(uint64_t at,const char* expected) { return names.count(at) && names.at(at)==expected; }
    CallIdentity capture(uint64_t object) {
        return objects.count(object) ? objects.at(object) : CallIdentity{-1,0,0};
    }
    bool identity(const CallIdentity& id) {
        const auto current=capture(id.address);
        return id.address && current.address==id.address && current.index==id.index && current.serial==id.serial;
    }
    uint64_t object(const char* name,uint64_t cls,uint64_t outer) {
        auto at=next; next+=0x1000;
        objects[at]={static_cast<int32_t>(objects.size()),1001,at};
        words[at+8]=0; words[at+0x10]=cls; words[at+0x20]=outer;
        names[at+0x18]=name;
        return at;
    }
    uint64_t field(uint64_t owner,const char* name,const char* type,uint64_t table,
                   uint32_t offset,uint32_t width,uint64_t flags) {
        auto at=next; next+=0x1000;
        words[at]=base+table; words[at+8]=at+0x800; names[at+0x800]=type;
        words[at+0x10]=owner|1; words[at+0x18]=0; names[at+0x20]=name;
        words[at+0x30]=1; words[at+0x34]=width; words[at+0x38]=flags; words[at+0x44]=offset;
        return at;
    }
};
struct Fixture {
    Memory memory;
    uint64_t core=0, slate=0, slate_core=0, script_struct=0;
    uint64_t vector=0,color=0,margin=0,anchors=0,parameter=0;
    Fixture() {
        auto package_class=memory.object("Package",0,0);
        core=memory.object("/Script/CoreUObject",package_class,0);
        slate=memory.object("/Script/Slate",package_class,0);
        slate_core=memory.object("/Script/SlateCore",package_class,0);
        script_struct=memory.object("ScriptStruct",0,core);
        vector=make("Vector2D",core,16,{"X","Y"},"DoubleProperty",0x6e11788,8,6755469251052037ULL);
        color=make("LinearColor",core,16,{"R","G","B","A"},"FloatProperty",0x6e11560,4,6755469251052037ULL);
        margin=make("Margin",slate_core,16,{"Left","Top","Right","Bottom"},"FloatProperty",0x6e11560,4,6755469234274821ULL);
        anchors=make("Anchors",slate,32,{"Minimum","Maximum"},"StructProperty",0x6e136a0,16,6755469234274821ULL);
        auto field=memory.words.at(anchors+0x50);
        memory.words[field+0x70]=vector;
        memory.words[memory.words.at(field+0x18)+0x70]=vector;
        parameter=memory.field(0xdead000,"Position","StructProperty",0x6e136a0,0,16,0x80);
        memory.words[parameter+0x70]=vector;
    }
    uint64_t make(const char* name,uint64_t package,uint32_t width,std::initializer_list<const char*> fields,
                  const char* type,uint64_t table,uint32_t component,uint64_t flags) {
        auto object=memory.object(name,script_struct,package);
        memory.words[object+0x40]=0; memory.words[object+0x58]=width;
        uint64_t link=object+0x50; uint32_t offset=0;
        for(auto field_name:fields) {
            auto field=memory.field(object,field_name,type,table,offset,component,flags);
            memory.words[link]=field; link=field+0x18; offset+=component;
        }
        return object;
    }
    bool check(uint64_t object,PodValueKind kind) {
        return validate_pod_schema(memory,kind,memory.capture(object));
    }
};

struct TimingFixture : Fixture {
    uint64_t number,time,rate,qualified,sub,ratefield;
    TimingFixture() {
        number=make("FrameNumber",core,4,{"Value"},"IntProperty",0x6e10a98,4,6755469234274821ULL);
        rate=make("FrameRate",core,8,{"Numerator","Denominator"},"IntProperty",0x6e10a98,4,6755469234274821ULL);
        time=make("FrameTime",core,8,{"FrameNumber","SubFrame"},"StructProperty",0x6e136a0,4,6755468160532484ULL);
        auto first=memory.words[time+0x50]; memory.words[first+0x70]=number;
        sub=memory.words[first+0x18]; memory.words[sub]=memory.base+0x6e11560;
        memory.names[memory.words[sub+8]]="FloatProperty"; memory.words[sub+0x38]=20266268116386308ULL;
        qualified=make("QualifiedFrameTime",core,16,{"Time","Rate"},"StructProperty",0x6e136a0,8,6755468160532484ULL);
        first=memory.words[qualified+0x50]; memory.words[first+0x70]=time;
        ratefield=memory.words[first+0x18]; memory.words[ratefield+0x70]=rate;
        memory.words[ratefield+0x38]=6755469234274820ULL;
    }
    bool valid() { return check(qualified,PodValueKind::QualifiedFrameTime); }
};
int main() {
    try {
        TimingFixture good; if(!good.valid()) return 1;
        for(auto kind:{PodValueKind::FrameNumber,PodValueKind::FrameTime,PodValueKind::FrameRate}) {
            TimingFixture t;auto object=kind==PodValueKind::FrameNumber ? t.number : kind==PodValueKind::FrameTime ? t.time : t.rate;
            if(!t.check(object,kind))return 8;
        }
        auto reject=[](auto change) { TimingFixture t; change(t); if(t.valid()) throw std::runtime_error("bad timing schema accepted"); };
        reject([](auto& t){t.memory.words[t.sub+0x38]=0;});
        reject([](auto& t){t.memory.words[t.sub+0x44]=0;});
        reject([](auto& t){t.memory.words[t.ratefield+0x70]=t.time;});
        reject([](auto& t){t.memory.words[t.rate+0x58]=4;});
        reject([](auto& t){t.memory.words[t.sub+0x18]=t.sub;});
        reject([](auto& t){t.memory.objects.erase(t.number);});
        reject([](auto& t){t.memory.live=false;});
        reject([](auto& t){t.memory.stop_after=2;});
        uint8_t value[16]{};
        if(!valid_pod_value(PodValueKind::QualifiedFrameTime,value,16)) return 2;
        uint32_t nan=0x7fc00000; std::memcpy(value+4,&nan,4);
        if(valid_pod_value(PodValueKind::QualifiedFrameTime,value,16)) return 3;
        CallPacket p{}; p.version=2;p.parameter_size=p.allocation_extent=16;
        p.return_offset=0;p.target={1,1,0x1000};p.function={2,1,0x2000};p.field_count=1;
        auto& f=p.fields[0];f.kind=19;f.width=16;f.dimension=1;f.flags=0x580;
        std::memcpy(f.name,"ReturnValue",sizeof("ReturnValue"));f.constraint={3,1,0x3000};
#ifdef E33_FRAME_TIME_SESSION
        if(validate_call_packet(p,true)) return 4;
        f.flags=0x80;p.return_offset=65535;
        if(!validate_call_packet(p,true)) return 5;
#else
        if(!validate_call_packet(p,true)) return 6;
#endif
    } catch(const std::exception& e) {std::cerr<<e.what();return 7;}
    return 0;
}
