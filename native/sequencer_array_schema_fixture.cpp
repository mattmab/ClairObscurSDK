#include "sequencer_array_schema.h"
#include <map>
#include <set>
#include <string>
#include <cassert>
struct Memory {
    uint64_t base=0x140000000ULL,next=0x10000;bool live=true;
    std::map<uint64_t,uint64_t> words;std::map<uint64_t,std::string> names;
    std::map<uint64_t,CallIdentity> objects;std::set<uint64_t> classes;
    bool context(){return live;}template<class T>T read(uint64_t p){return static_cast<T>(words[p]);}
    bool name(uint64_t p,const char* s){return names[p]==s;}
    bool registered(uint64_t p){return p && objects.count(p)!=0;}
    bool is_class(uint64_t p){return classes.count(p)!=0;}
    CallIdentity capture(uint64_t p){return registered(p) ? objects[p] : CallIdentity{};}
    bool identity(const CallIdentity& id){const auto c=capture(id.address);return id.address && id.index==c.index && id.serial==c.serial && id.address==c.address;}
    bool derives(uint64_t c,uint64_t parent){for(unsigned i=0;c && i<128;++i,c=words[c+0x40])if(c==parent)return true;return false;}
    uint64_t object(const char* n,uint64_t cls=0,uint64_t outer=0){auto p=next;next+=0x1000;objects[p]={int32_t(objects.size()),1,p};names[p+24]=n;words[p+16]=cls;words[p+32]=outer;return p;}
    uint64_t cls(const char* n,uint64_t package,uint64_t parent=0){auto p=object(n,0,package);classes.insert(p);words[p+0x40]=parent;return p;}
    uint64_t property(uint64_t owner,const char* n,const char* type,uint32_t offset,uint32_t width,uint64_t table,uint64_t flags){auto p=next;next+=0x1000;names[p+32]=n;names[p+0x800]=type;words[p]=base+table;words[p+8]=p+0x800;words[p+16]=owner|1;words[p+0x30]=1;words[p+0x34]=width;words[p+0x38]=flags;words[p+0x44]=offset;return p;}
};
struct Fixture {
    Memory m;e33_sequencer_array::Packet p{};uint64_t fn,input,result,inner,section_class,output_class;
    Fixture(bool keys=false){
        const auto seq=m.object("/Script/SequencerScripting"),movie=m.object("/Script/MovieScene");
        const auto owner=m.cls(keys ? "MovieSceneScriptingDoubleChannel" : "MovieSceneSectionExtensions",seq);
        section_class=m.cls("MovieSceneSection",movie);
        const auto subject_class=keys ? owner : m.cls("MovieScene3DTransformSection",movie,section_class);
        const auto subject=m.object("OwnedSectionOrChannel",subject_class);
        auto target=keys ? subject : m.object("Default__MovieSceneSectionExtensions",owner,seq);
        if(!keys)m.words[target+8]=0x10;
        const auto vt=m.next;m.next+=0x1000;m.words[target]=vt;m.words[vt+0x268]=m.base+0x1393330;
        fn=m.object(keys ? "GetKeys" : "GetAllChannels",0,owner);m.words[fn]=m.base+0x6dea198;
        m.words[fn+0xb0]=keys ? 1409418240 : 67249153;m.words[fn+0xb6]=keys ? 16 : 24;
        m.words[fn+0xb8]=keys ? 0 : 8;m.words[fn+0x58]=keys ? 16 : 24;m.words[fn+0xd8]=m.base+(keys ? 0x3208d90 : 0x4ae93a0);
        result=m.property(fn,"ReturnValue","ArrayProperty",keys ? 0 : 8,16,0x6e0de80,4503599627372416ULL);
        input=keys ? 0 : m.property(fn,"Section","ObjectProperty",0,8,0x6e11d38,6755468161057408ULL);
        if(input){m.words[input+0x70]=section_class;m.words[input+24]=result;}
        m.words[fn+0x50]=input ? input : result;
        inner=m.property(result,"ReturnValue","ObjectProperty",0,8,0x6e11d38,0);m.words[inner+16]=result;
        output_class=m.cls(keys ? "MovieSceneScriptingKey" : "MovieSceneScriptingChannel",seq);
        m.words[inner+0x70]=output_class;m.words[result+0x78]=inner;
        p.version=3;p.op=220;p.request=1;p.mode=keys ? 2 : 1;p.target=m.capture(target);p.subject=m.capture(subject);p.function=m.capture(fn);p.subject_token=1;
    }
    bool valid(){return sequencer_array_schema(m,p);}
};
int main(){
    {Fixture f;assert(f.valid());}{Fixture f(true);assert(f.valid());}
    for(unsigned i=0;i<10;++i){Fixture f;if(i==0)f.m.live=false;if(i==1)f.m.words[f.fn+0xd8]++;
        if(i==2)f.m.words[f.inner+16]|=1;if(i==3)f.m.words[f.inner+0x34]=16;if(i==4)f.m.words[f.result+0x70]=1;
        if(i==5)f.m.words[f.result+24]=f.result;if(i==6)f.m.words[f.input+0x70]=f.output_class;
        if(i==7)f.p.function.serial++;if(i==8)f.m.words[f.result+0x38]++;if(i==9)f.m.words[f.fn+0xb6]=16;
        assert(!f.valid());}
    {Fixture f(true);f.p.target.serial++;assert(!f.valid());}
    {Fixture f(true);f.m.words[f.fn+0xb0]=67249153;assert(!f.valid());}
    return 0;
}
