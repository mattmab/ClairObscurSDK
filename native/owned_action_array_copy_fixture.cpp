#include "owned_action_array_copy.h"
#include "owned_action_array_schema.h"
#include <cassert>
#include <array>
#include <map>
#include <set>
#include <string>
using namespace e33_action_clone;
struct SchemaMemory {
    uint64_t base=0x10000000,next=0x10000;std::map<uint64_t,uint8_t> data;
    std::map<uint64_t,std::string> names;std::set<uint64_t> classes;
    template<class T> T read(uint64_t at) {T value{};auto* p=reinterpret_cast<uint8_t*>(&value);for(unsigned i=0;i<sizeof(T);++i)p[i]=data[at+i];return value;}
    template<class T> void put(uint64_t at,T value) {auto* p=reinterpret_cast<uint8_t*>(&value);for(unsigned i=0;i<sizeof(T);++i)data[at+i]=p[i];}
    bool registered(uint64_t at) {return names.count(at+24)!=0;}
    bool is_class(uint64_t at) {return classes.count(at)!=0;}
    bool name(uint64_t at,const char* value) {return names.count(at)&&names[at]==value;}
    uint64_t object(const char* name,uint64_t outer=0) {auto at=next;next+=0x100;names[at+24]=name;put(at+32,outer);return at;}
    uint64_t property(uint64_t owner,const char* name,const char* type,unsigned offset,unsigned width,uint64_t table,uint64_t flags) {
        auto at=next;next+=0x100;auto t=next;next+=0x100;names[at+32]=name;names[t]=type;
        put(at,base+table);put(at+8,t);put(at+16,owner|1);put(at+0x30,1U);put(at+0x34,width);put(at+0x38,flags);put(at+0x44,offset);return at;
    }
};
static void exact_schema_fixture() {
    SchemaMemory m;
    auto package=m.object("/Game/Gameplay/GameActionsSystem/SequentialGameAction/BP_GameAction_Sequential");
    auto sandfall=m.object("/Script/SandFall"),core=m.object("/Script/CoreUObject");
    auto cls=m.object("BP_GameAction_Sequential_C",package),action=m.object("GameAction",sandfall);
    m.classes.insert(cls);m.classes.insert(action);m.put(cls+0x58,64U);
    auto scriptstruct=m.object("ScriptStruct",core),wrapper=m.object("GameAction_Wrapper",sandfall);
    m.put(wrapper+16,scriptstruct);m.put(wrapper+0x58,16U);
    auto field=m.property(cls,"GameActionsToExecute","ArrayProperty",48,16,0x6e0de80,549755813893ULL);
    m.put(cls+0x50,field);
    auto inner=m.property(field,"GameActionsToExecute","StructProperty",0,16,0x6e136a0,0);
    m.put(inner+16,field);m.put(field+0x78,inner);m.put(inner+0x70,wrapper);
    auto reference=m.property(wrapper,"GameActionReference","ObjectProperty",0,8,0x6e11d38,6755468160532997ULL);
    auto inlined=m.property(wrapper,"GameActionInline","ObjectProperty",8,8,0x6e11d38,7318418114478605ULL);
    m.put(wrapper+0x50,reference);m.put(reference+24,inlined);m.put(reference+0x70,action);m.put(inlined+0x70,action);
    assert(simon_root_array_schema(m,cls)==field);
    {auto bad=m;bad.put(field+0x44,40U);assert(!simon_root_array_schema(bad,cls));}
    {auto bad=m;bad.put(inner+16,field|1);assert(!simon_root_array_schema(bad,cls));}
    {auto bad=m;bad.put(inlined+0x38,6755468160532997ULL);assert(!simon_root_array_schema(bad,cls));}
    {auto bad=m;bad.put(inlined+0x70,cls);assert(!simon_root_array_schema(bad,cls));}
    {auto bad=m;bad.put(wrapper+0x58,24U);assert(!simon_root_array_schema(bad,cls));}
    {auto bad=m;bad.names[sandfall+24]="/Script/Other";assert(!simon_root_array_schema(bad,cls));}
}
struct Ops {
    uint64_t base=0x10000000,entry=base+array_copy_entry,table=base+array_property_table;
    bool current=true,profile=true,prefix=true,independent=true,alias=false,unknown=false;
    unsigned calls=0;
    std::array<uint64_t,20> source{},destination{};
    Ops() {for(unsigned i=0;i<10;++i)source[i*2+(simon_wrapper_inline[i] ? 1 : 0)]=i+1;}
    bool context() {return current;}
    template<class T> T read(uint64_t address) {
        return T(address==base+array_property_table+0xf0 ? entry : address==0x20000 ? table : 0);
    }
    bool bytes(uint64_t address,const uint8_t* p,size_t n) {
        return prefix && address==base+array_copy_entry && n==sizeof(array_copy_prefix) &&
            !std::memcmp(p,array_copy_prefix,n);
    }
    bool admit_exact_simon_root_array(RootArrayCopy& copy) {
        if(!profile)return false;
        copy={0x20000,0x30000,alias ? 0x30000U : 0x40000U};return true;
    }
    void publish_array_copy_unknown(const RootArrayCopy&) {unknown=true;}
    void copy_array(const RootArrayCopy&) {assert(unknown);++calls;destination=source;}
    bool verify_independent_simon_array_and_unchanged_source(const RootArrayCopy&) {
        return independent && destination==source;
    }
};
int main() {
    exact_schema_fixture();
    {Ops o;assert(copy_owned_simon_wrappers(o)==Result::returned);assert(o.calls==1);assert(o.destination==o.source);}
    {Ops o;o.current=false;assert(copy_owned_simon_wrappers(o)==Result::not_dispatched);assert(!o.calls && !o.unknown);}
    {Ops o;o.profile=false;assert(copy_owned_simon_wrappers(o)==Result::not_dispatched);assert(!o.calls);}
    {Ops o;o.alias=true;assert(copy_owned_simon_wrappers(o)==Result::not_dispatched);assert(!o.calls);}
    {Ops o;++o.entry;assert(copy_owned_simon_wrappers(o)==Result::not_dispatched);assert(!o.calls);}
    {Ops o;++o.table;assert(copy_owned_simon_wrappers(o)==Result::not_dispatched);assert(!o.calls);}
    {Ops o;o.prefix=false;assert(copy_owned_simon_wrappers(o)==Result::not_dispatched);assert(!o.calls);}
    {Ops o;o.independent=false;assert(copy_owned_simon_wrappers(o)==Result::unknown);assert(o.calls==1 && o.unknown);}
}
