#include "target_pod_schema.h"
#include <map>
#include <string>
#include <stdexcept>
#include <iostream>

// Compile the real local-memory adapter/template combination without executing
// it in this standalone fixture. Live game-thread validation remains separate.
bool compile_target_pod_schema(uint64_t base,uint64_t property,const CallIdentity& id) {
    TargetPodSchemaOps ops{base};
    return validate_pod_parameter(ops,property,PodValueKind::Anchors,id);
}

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
        Fixture f;
        if(!f.check(f.vector,PodValueKind::Vector2D) || !f.check(f.color,PodValueKind::LinearColor) ||
           !f.check(f.margin,PodValueKind::Margin) || !f.check(f.anchors,PodValueKind::Anchors) ||
           !validate_pod_parameter(f.memory,f.parameter,PodValueKind::Vector2D,f.memory.capture(f.vector))) return 1;
        unsigned rejected=0;
        auto reject=[&](auto change) {
            Fixture test;
            change(test);
            if(test.check(test.anchors,PodValueKind::Anchors)) throw std::runtime_error("accepted altered schema");
            ++rejected;
        };
        reject([](auto& t){ t.memory.live=false; });
        reject([](auto& t){ t.memory.stop_after=1; });
        reject([](auto& t){ t.memory.words[t.anchors+8]=0x40000000; });
        reject([](auto& t){ t.memory.names[t.slate+0x18]="/Script/Other"; });
        reject([](auto& t){ t.memory.words[t.slate+0x20]=t.core; });
        reject([](auto& t){ t.memory.names[t.script_struct+0x18]="Class"; });
        reject([](auto& t){ t.memory.words[t.anchors+0x40]=t.vector; });
        reject([](auto& t){ t.memory.words[t.anchors+0x58]=16; });
        reject([](auto& t){ t.memory.words[t.anchors+0x50]=0; });
        reject([](auto& t){ auto p=t.memory.words.at(t.anchors+0x50); t.memory.words[p+0x70]=t.color; });
        reject([](auto& t){ auto p=t.memory.words.at(t.anchors+0x50); t.memory.words[p+0x18]=p; });
        reject([](auto& t){ auto p=t.memory.words.at(t.vector+0x50); t.memory.words[p]=t.memory.base+0x6e11560; });
        reject([](auto& t){ auto p=t.memory.words.at(t.vector+0x50); t.memory.words[p+0x10]=t.anchors|1; });
        reject([](auto& t){ auto p=t.memory.words.at(t.vector+0x50); t.memory.words[p+0x30]=2; });
        reject([](auto& t){ auto p=t.memory.words.at(t.vector+0x50); t.memory.words[p+0x34]=4; });
        reject([](auto& t){ auto p=t.memory.words.at(t.vector+0x50); t.memory.words[p+0x38]=0; });
        reject([](auto& t){ auto p=t.memory.words.at(t.vector+0x50); t.memory.words[p+0x44]=4; });
        reject([](auto& t){ auto p=t.memory.words.at(t.vector+0x50); t.memory.names[p+0x20]="Z"; });
        reject([](auto& t){ auto p=t.memory.words.at(t.vector+0x50); t.memory.names[t.memory.words.at(p+8)]="ObjectProperty"; });
        reject([](auto& t){ auto p=t.memory.words.at(t.vector+0x50); auto q=t.memory.words.at(p+0x18); t.memory.words[q+0x18]=p; });
        reject([](auto& t){ t.memory.objects.erase(t.vector); });
        auto stale=f.memory.capture(f.vector); ++stale.serial;
        if(validate_pod_schema(f.memory,PodValueKind::Vector2D,stale)) return 2;
        if(validate_pod_schema(f.memory,static_cast<PodValueKind>(99),f.memory.capture(f.vector))) return 3;
        f.memory.words[f.parameter+0x70]=f.color;
        if(validate_pod_parameter(f.memory,f.parameter,PodValueKind::Vector2D,f.memory.capture(f.vector))) return 4;
        std::cout << "Four profiles and parameter binding passed; " << rejected+3 << " altered/context/identity cases rejected.\n";
    } catch(const std::exception& error) { std::cerr << error.what() << '\n'; return 5; }
    return 0;
}
