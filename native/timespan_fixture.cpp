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


int main() {
 try {
  Fixture t;auto ts=t.make("Timespan",t.core,8,{},"",0,0,0);t.memory.words[ts+0x50]=0;
  if(!t.check(ts,PodValueKind::Timespan)) return 1;
  t.memory.words[ts+0x50]=1;if(t.check(ts,PodValueKind::Timespan))return 2;t.memory.words[ts+0x50]=0;
  t.memory.words[ts+0x58]=16;if(t.check(ts,PodValueKind::Timespan))return 3;t.memory.words[ts+0x58]=8;
  auto id=t.memory.capture(ts);++id.serial;if(validate_pod_schema(t.memory,PodValueKind::Timespan,id))return 4;
  CallPacket p{};p.version=2;p.parameter_size=p.allocation_extent=8;p.return_offset=0;p.target={1,1,0x1000};p.function={2,1,0x2000};p.field_count=1;p.function_flags=1417806851;p.entry_rva=0x3208990;
  auto& f=p.fields[0];f.kind=20;f.width=8;f.dimension=1;f.flags=6755468160534400ULL;std::memcpy(f.name,"ReturnValue",sizeof("ReturnValue"));f.constraint={3,1,0x3000};
#ifdef E33_TIMESPAN_SESSION
  if(validate_call_packet(p,true))return 5;
  p.entry_rva=0x3207a70;if(validate_call_packet(p,true))return 6;
  for(auto version:{1u,3u,4u,5u,6u,7u}){p.version=version;if(!validate_call_packet(p,true))return 7;}p.version=2;
  p.entry_rva=1;if(!validate_call_packet(p,true))return 8;p.entry_rva=0x3208990;
  f.flags=0x80;p.return_offset=65535;if(!validate_call_packet(p,true))return 9;p.return_offset=0;f.flags=6755468160534400ULL;
  f.dimension=2;if(!validate_call_packet(p,true))return 10;f.dimension=1;
  f.offset=1;if(!validate_call_packet(p,true))return 11;f.offset=0;
  p.data[0]=1;if(!validate_call_packet(p,true))return 12;p.data[0]=0;
#else
  if(!validate_call_packet(p,true))return 13;
#endif
  uint8_t value[8];std::memset(value,0xff,8);if(!valid_pod_value(PodValueKind::Timespan,value,8)||valid_pod_value(PodValueKind::Timespan,value,7))return 14;
  std::cout<<"Timespan fixture passed\n";
 } catch(const std::exception& e){std::cerr<<e.what();return 20;}
}
