#include "sequence_origin_journal.h"
#include "sequence_origin_schema.h"
#include "sequence_cleanup_admission.h"
#include <cassert>
#include <limits>
#include <map>
#include <set>
#include <string>
#include <cstring>
struct Memory {
    uint64_t base=0x10000000,next=0x10000;
    std::map<uint64_t,uint8_t> bytes;std::map<uint64_t,std::string> names;
    std::set<uint64_t> classes;
    template<class T> T read(uint64_t p) {T v{};auto* b=reinterpret_cast<uint8_t*>(&v);for(unsigned i=0;i<sizeof(T);++i)b[i]=bytes[p+i];return v;}
    template<class T> void put(uint64_t p,T v) {const auto* b=reinterpret_cast<const uint8_t*>(&v);for(unsigned i=0;i<sizeof(T);++i)bytes[p+i]=b[i];}
    bool registered(uint64_t p) {return names.count(p+24)!=0;}
    bool is_class(uint64_t p) {return classes.count(p)!=0;}
    bool name(uint64_t p,const char* s) {return names.count(p)&&names[p]==s;}
    uint64_t object(const char* n) {const auto p=next;next+=0x100;names[p+24]=n;return p;}
    uint64_t scalar(const char* n,unsigned count,uint64_t package,uint64_t cls) {
        const auto s=object(n);put(s+32,package);put(s+16,cls);put(s+0x58,count*8);
        const char* components[]={"X","Y","Z","W"};uint64_t previous=0;
        for(unsigned i=0;i<count;++i) {const auto f=property(s,components[i],"DoubleProperty",i*8,8,0x6e11788,6755469251052037ULL);
            if(previous)put(previous+24,f);else put(s+0x50,f);previous=f;}
        return s;
    }
    uint64_t property(uint64_t owner,const char* n,const char* type,unsigned offset,unsigned width,uint64_t table,uint64_t flags) {
        const auto p=next;next+=0x100;const auto t=next;next+=0x100;
        names[p+32]=n;names[t]=type;put(p,base+table);put(p+8,t);put(p+16,owner|1);
        put(p+0x30,1U);put(p+0x34,width);put(p+0x38,flags);put(p+0x44,offset);return p;
    }
};
struct Ops {
    bool proof=true,write=true,verify=true;unsigned writes=0;
    SequenceOriginPacket observed{};
    bool prove_private_fresh() {return proof;}
    bool prove_private_current(const SequenceOriginPacket& p) {observed=p;return proof;}
    bool write_translation(const SequenceOriginPacket&) {++writes;return write;}
    bool verify_translation(const SequenceOriginPacket&) {return verify;}
};
static void schema_fixture() {
    Memory m;const auto package=m.object("/Script/CoreUObject"),cls=m.object("ScriptStruct");m.put(cls+32,package);
    const auto quat=m.scalar("Quat",4,package,cls),vector=m.scalar("Vector",3,package,cls),s=m.object("Transform");
    m.put(s+32,package);m.put(s+16,cls);m.put(s+0x58,96U);
    const char* names[]={"Rotation","Translation","Scale3D"};uint64_t fields[3]{};
    for(unsigned i=0;i<3;++i) {fields[i]=m.property(s,names[i],"StructProperty",i*32,i ? 24 : 32,0x6e136a0,
            i ? 6755469251052037ULL : 6755469251051525ULL);m.put(fields[i]+0x70,i ? vector : quat);
        if(i)m.put(fields[i-1]+24,fields[i]);else m.put(s+0x50,fields[i]);}
    SequenceOriginSchema<Memory> profile(m);assert(profile.transform(s));
    {auto bad=m;bad.put(fields[1]+0x44,40U);assert(!SequenceOriginSchema<Memory>(bad).transform(s));}
    {auto bad=m;bad.put(fields[0],m.base+0x6e11d38);assert(!SequenceOriginSchema<Memory>(bad).transform(s));}
    {auto bad=m;bad.put(fields[2]+24,fields[0]);assert(!SequenceOriginSchema<Memory>(bad).transform(s));}
    {auto bad=m;bad.names[package+24]="/Script/Other";assert(!SequenceOriginSchema<Memory>(bad).transform(s));}
    {auto bad=m;bad.put(fields[1]+0x70,quat);assert(!SequenceOriginSchema<Memory>(bad).transform(s));}
    {auto bad=m;bad.put(s+0x58,48U);assert(!SequenceOriginSchema<Memory>(bad).transform(s));}
    const auto level_package=m.object("/Script/LevelSequence"),engine_package=m.object("/Script/Engine");
    const auto ac=m.object("LevelSequenceActor"),dc=m.object("DefaultLevelSequenceInstanceData");
    m.classes.insert(ac);m.classes.insert(dc);m.put(ac+32,level_package);m.put(dc+32,level_package);
    const auto object_class=m.object("Object"),actor_class=m.object("Actor");m.put(object_class+32,package);m.put(actor_class+32,engine_package);
    m.classes.insert(object_class);m.classes.insert(actor_class);
    const auto ov=m.property(ac,"bOverrideInstanceData","BoolProperty",760,1,0x6e119b0,6755468160532485ULL);
    const auto di=m.property(ac,"DefaultInstanceData","ObjectProperty",768,8,0x6e11d38,80501912059249164ULL);
    m.put(ac+0x50,ov);m.put(ov+24,di);m.put(ov+0x70,0x02020001U);m.put(di+0x70,object_class);
    const auto oa=m.property(dc,"TransformOriginActor","ObjectProperty",48,8,0x6e11d38,79938962105303557ULL);
    const auto ot=m.property(dc,"TransformOrigin","StructProperty",64,96,0x6e136a0,6755469234274309ULL);
    m.put(dc+0x50,oa);m.put(oa+24,ot);m.put(oa+0x70,actor_class);m.put(ot+0x70,s);
    const auto actor=m.object("OwnedActor"),instance=m.object("InstanceData");m.put(actor+16,ac);m.put(instance+16,dc);
    m.put(instance+32,actor);m.put(actor+768,instance);
    assert(SequenceOriginSchema<Memory>(m).private_instance(actor,instance));
    {auto bad=m;bad.put(instance+32,uint64_t(999));assert(!SequenceOriginSchema<Memory>(bad).private_instance(actor,instance));}
    {auto bad=m;bad.put(actor+768,uint64_t(0));assert(!SequenceOriginSchema<Memory>(bad).private_instance(actor,instance));}
    {auto bad=m;bad.put(instance+48,actor);assert(!SequenceOriginSchema<Memory>(bad).private_instance(actor,instance));}
    {auto bad=m;bad.put(instance+8,0x10U);assert(!SequenceOriginSchema<Memory>(bad).private_instance(actor,instance));}
    {auto bad=m;bad.put(ov+0x70,0xff010001U);assert(!SequenceOriginSchema<Memory>(bad).private_instance(actor,instance));}
    {auto bad=m;bad.put(di+0x70,actor_class);assert(!SequenceOriginSchema<Memory>(bad).private_instance(actor,instance));}
    {auto bad=m;bad.classes.erase(dc);assert(!SequenceOriginSchema<Memory>(bad).private_instance(actor,instance));}
}
static void composite_cleanup_fixture() {
    struct Call {unsigned target,function,outcome;};
    const Call stop{1,10,0},destroy{2,20,0};
    SequenceCleanupAdmission<Call> admission;
    e33_sequence_origin::Journal origin;
    Ops ops;const SequenceOriginPacket p{0x4f533345,1,1.,2.,3.};
    assert(origin.configure(ops,p)==e33_sequence_origin::Result::ok);
    unsigned state=1,step=0;
    auto hook=[&](const Call& call) {
        if(call.target!=stop.target)return true;
        if(admission.allows(call))return true;
        return state==1 && origin.before_evaluation();
    };
    auto call=stop;state=2;
    assert(!hook(call)); // The original regression: composite owner is uncertain.
    assert(admission.begin(call,stop));
    auto forged=call;assert(!hook(forged)); // Same bytes, different invocation.
    assert(hook(call));call.outcome=1;admission.end();++step;state=1;
    assert(!admission.allows(call));
    call=destroy;state=2;assert(hook(call));call.outcome=1;++step;state=0;
    assert(step==2 && state==0);
    // A failed/unknown Stop cannot acquire a second admission after its window.
    auto unknown=stop;unknown.outcome=2;assert(!admission.begin(unknown,stop));
}
int main() {
    schema_fixture();
    composite_cleanup_fixture();
    using namespace e33_sequence_origin;
    const SequenceOriginPacket p{0x4f533345,1,120.,-20.,402000.};
    {Journal j;Ops o;assert(j.configure(o,p)==Result::ok);assert(o.writes==1);
     assert(j.configure(o,p)==Result::rejected);assert(j.before_evaluation());}
    {Journal j;Ops o;o.proof=false;assert(j.configure(o,p)==Result::rejected);assert(!o.writes);}
    {Journal j;Ops o;assert(j.before_evaluation());assert(j.configure(o,p)==Result::rejected);assert(!o.writes);}
    {Journal j;Ops o;o.verify=false;assert(j.configure(o,p)==Result::unknown);
     assert(j.quarantined());assert(!j.before_evaluation());assert(j.configure(o,p)==Result::rejected);assert(o.writes==1);}
    {Journal j;Ops o;o.write=false;assert(j.configure(o,p)==Result::unknown);
     assert(!j.before_evaluation());assert(j.configure(o,p)==Result::rejected);assert(o.writes==1);}
    {Journal j;Ops o;auto bad=p;bad.x=std::numeric_limits<double>::infinity();
     assert(j.configure(o,bad)==Result::rejected);assert(!o.writes);}
    {Journal j;Ops o;assert(j.update(o,p)==Result::rejected);assert(!o.writes);
     assert(j.before_evaluation());assert(j.update(o,p)==Result::rejected);assert(!o.writes);}
    {Journal j;Ops o;assert(j.configure(o,p)==Result::ok);assert(j.before_evaluation());
     auto moved=p;moved.x+=100.;assert(j.update(o,moved)==Result::ok);
     assert(o.observed.x==p.x && o.writes==2);assert(j.before_evaluation());
     moved.y+=250.;assert(j.update(o,moved)==Result::ok);assert(o.observed.y==p.y && o.observed.x==moved.x);
     o.proof=false;assert(j.update(o,p)==Result::rejected);assert(o.writes==3);assert(j.before_evaluation());}
    {Journal j;Ops o;assert(j.configure(o,p)==Result::ok);o.verify=false;
     assert(j.update(o,p)==Result::unknown);assert(j.quarantined());assert(!j.before_evaluation());
     assert(j.update(o,p)==Result::rejected);assert(j.configure(o,p)==Result::rejected);assert(o.writes==2);}
    struct TransformOps {
        bool proof=true,write=true,verify=true;unsigned writes=0;
        SequenceOriginTransformPacket observed{};
        bool prove_private_fresh(){return proof;}
        bool prove_transform_current(const SequenceOriginTransformPacket& value){observed=value;return proof;}
        bool write_transform(const SequenceOriginTransformPacket&){++writes;return write;}
        bool verify_transform(const SequenceOriginTransformPacket&){return verify;}
    };
    const SequenceOriginTransformPacket t{0x54533345,1,120.,-20.,402000.,90.};
    {double q[4]{};sequence_origin_transform_quaternion(t,q);
     assert(q[0]==0. && q[1]==0. && std::abs(q[2]-std::sqrt(.5))<1e-14 && std::abs(q[3]-std::sqrt(.5))<1e-14);}
    {TransformJournal j;TransformOps o;assert(j.configure(o,t)==Result::ok);assert(j.before_evaluation());
     auto changed=t;changed.yaw=-90.;changed.x+=2.;assert(j.update(o,changed)==Result::ok);
     assert(o.observed.yaw==90. && o.writes==2);o.proof=false;
     assert(j.update(o,t)==Result::rejected);assert(o.writes==2);}
    {TransformJournal j;TransformOps o;auto bad=t;bad.yaw=181.;assert(j.configure(o,bad)==Result::rejected);assert(!o.writes);
     bad=t;bad.yaw=std::numeric_limits<double>::quiet_NaN();assert(j.configure(o,bad)==Result::rejected);assert(!o.writes);}
    {TransformJournal j;TransformOps o;assert(j.configure(o,t)==Result::ok);o.verify=false;
     assert(j.update(o,t)==Result::unknown);assert(!j.before_evaluation());assert(j.update(o,t)==Result::rejected);}
}
