#include "sequence_seek_schema.h"
#include <map>
#include <set>
#include <string>
#include <vector>
#include <cassert>
struct Memory {
    uint64_t base=0x140000000ULL,next=0x10000;
    std::map<uint64_t,uint64_t> words;
    std::map<uint64_t,std::string> names;
    std::map<uint64_t,CallIdentity> objects;
    std::set<uint64_t> classes;
    bool live=true;
    bool context(){return live;}
    template<class T>T read(uint64_t p){return static_cast<T>(words[p]);}
    bool name(uint64_t p,const char* expected){return names.count(p) && names[p]==expected;}
    CallIdentity capture(uint64_t p){return objects.count(p) ? objects[p] : CallIdentity{};}
    bool registered(uint64_t p){return p && objects.count(p)!=0;}
    bool is_class(uint64_t p){return classes.count(p)!=0;}
    bool identity(const CallIdentity& id){const auto now=capture(id.address);return id.address && now.address==id.address && now.index==id.index && now.serial==id.serial;}
    uint64_t object(const char* name,uint64_t cls=0,uint64_t outer=0){
        const auto p=next;next+=0x1000;objects[p]={int32_t(objects.size()),1,p};
        names[p+24]=name;words[p+16]=cls;words[p+32]=outer;return p;
    }
    uint64_t property(uint64_t owner,const char* name,const char* type,unsigned offset,unsigned width,uint64_t table,uint64_t flags){
        const auto p=next;next+=0x1000;names[p+32]=name;names[p+0x800]=type;
        words[p]=base+table;words[p+8]=p+0x800;words[p+16]=owner|1;words[p+0x30]=1;
        words[p+0x34]=width;words[p+0x38]=flags;words[p+0x44]=offset;return p;
    }
    void chain(uint64_t owner,const std::vector<uint64_t>& fields){
        words[owner+0x50]=fields[0];for(size_t i=1;i<fields.size();++i)words[fields[i-1]+24]=fields[i];
    }
};
struct Fixture {
    Memory m;uint64_t core,movie,script,fn,params,timecode,marked,boolfield,enumfield;
    Fixture(){
        const auto package=m.object("Package");core=m.object("/Script/CoreUObject",package);movie=m.object("/Script/MovieScene",package);
        script=m.object("ScriptStruct",0,core);
        const auto number=structure("FrameNumber",core,4),time=structure("FrameTime",core,8);
        m.chain(number,{m.property(number,"Value","IntProperty",0,4,0x6e10a98,6755469234274821ULL)});
        const auto n=m.property(time,"FrameNumber","StructProperty",0,4,0x6e136a0,6755468160532484ULL);
        m.words[n+0x70]=number;
        m.chain(time,{n,m.property(time,"SubFrame","FloatProperty",4,4,0x6e11560,20266268116386308ULL)});
        timecode=structure("Timecode",core,20);std::vector<uint64_t> tc;
        const char* tcn[]={"Hours","Minutes","Seconds","Frames","bDropFrameFormat"};
        for(unsigned i=0;i<5;++i)tc.push_back(m.property(timecode,tcn[i],i==4?"BoolProperty":"IntProperty",i*4,i==4?1:4,i==4?0x6e119b0:0x6e10a98,6755469234274820ULL));
        m.words[tc[4]+0x70]=0xff010001;m.chain(timecode,tc);
        params=structure("MovieSceneSequencePlaybackParams",movie,56);
        const auto frame=m.property(params,"Frame","StructProperty",0,8,0x6e136a0,6755468160532485ULL);m.words[frame+0x70]=time;
        const auto seconds=m.property(params,"Time","FloatProperty",8,4,0x6e11560,6755469234274821ULL);
        marked=m.property(params,"MarkedFrame","StrProperty",16,16,0x6e131d8,6755399441056261ULL);
        const auto tcfield=m.property(params,"Timecode","StructProperty",32,20,0x6e136a0,6755469234274821ULL);m.words[tcfield+0x70]=timecode;
        enumfield=m.property(params,"PositionType","EnumProperty",52,1,0x6deeee8,6755469234274821ULL);
        enumeration(enumfield,"EMovieScenePositionType",{"EMovieScenePositionType::Frame","EMovieScenePositionType::Time","EMovieScenePositionType::MarkedFrame","EMovieScenePositionType::Timecode","EMovieScenePositionType::EMovieScenePositionType_MAX"});
        const auto update=m.property(params,"UpdateMethod","EnumProperty",53,1,0x6deeee8,6755469234274821ULL);
        enumeration(update,"EUpdatePositionMethod",{"EUpdatePositionMethod::Play","EUpdatePositionMethod::Jump","EUpdatePositionMethod::Scrub","EUpdatePositionMethod::EUpdatePositionMethod_MAX"});
        boolfield=m.property(params,"bHasJumped","BoolProperty",54,1,0x6e119b0,6755469234274821ULL);m.words[boolfield+0x70]=0xff010001;
        m.chain(params,{frame,seconds,marked,tcfield,enumfield,update,boolfield});
        const auto owner=m.object("MovieSceneSequencePlayer",0,movie),function=m.object("Function",0,core);m.classes.insert(owner);
        fn=m.object("SetPlaybackPosition",function,owner);m.words[fn+0xb0]=67240963;m.words[fn+0xb6]=56;m.words[fn+0xb8]=65535;
        m.words[fn+0x58]=56;m.words[fn+0xd8]=m.base+0x2d6a350;
        const auto f=m.property(fn,"PlaybackParams","StructProperty",0,56,0x6e136a0,4503599627370624ULL);m.words[f+0x70]=params;m.chain(fn,{f});
    }
    uint64_t structure(const char* name,uint64_t package,unsigned width){const auto p=m.object(name,script,package);m.words[p+0x58]=width;return p;}
    void enumeration(uint64_t p,const char* name,const std::vector<const char*>& members){
        const auto cls=m.object("Enum",0,core),e=m.object(name,cls,movie),data=m.next;m.next+=0x1000;
        m.words[e]=m.base+0x6dee0b0;m.words[e+0x40]=data;m.words[e+0x48]=members.size();m.words[e+0x4c]=members.size();
        for(size_t i=0;i<members.size();++i){m.names[data+16*i]=members[i];m.words[data+16*i+8]=i;}
        const auto child=m.property(p,"UnderlyingType","ByteProperty",0,1,0,0);m.words[child+16]=p;
        m.words[p+0x70]=child;m.words[p+0x78]=e;
    }
    bool valid(){return SequenceSeekSchema<Memory>(m).function(m.capture(fn));}
};
int main(){
    Fixture f;assert(f.valid());
    {auto x=f;x.m.live=false;assert(!x.valid());}
    {auto x=f;x.m.words[x.fn+0xd8]++;assert(!x.valid());}
    {auto x=f;x.m.words[x.fn+0xb6]=48;assert(!x.valid());}
    {auto x=f;x.m.words[x.params+0x58]=64;assert(!x.valid());}
    {auto x=f;x.m.words[x.marked+0x44]=8;assert(!x.valid());}
    {auto x=f;x.m.words[x.marked+0x34]=8;assert(!x.valid());}
    {auto x=f;x.m.words[x.boolfield+0x70]=0x01010001;assert(!x.valid());}
    {auto x=f;x.m.words[x.boolfield+24]=x.marked;assert(!x.valid());}
    {auto x=f;x.m.words[x.timecode+0x58]=16;assert(!x.valid());}
    {auto x=f;const auto e=x.m.words[x.enumfield+0x78],data=x.m.words[e+0x40];x.m.words[data+8]=2;assert(!x.valid());}
    {auto x=f;const auto e=x.m.words[x.enumfield+0x78];x.m.words[e+0x48]=4;assert(!x.valid());}
    {auto x=f;x.m.names[x.movie+24]="/Script/Other";assert(!x.valid());}
    {auto id=f.m.capture(f.fn);id.serial++;assert(!SequenceSeekSchema<Memory>(f.m).function(id));}
}
