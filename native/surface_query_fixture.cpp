#include "surface_query.h"
#include <cassert>
#include <limits>
using e33_surface_query::Result;
struct Fake {
    int calls=0;bool trace=true,blocking=true,overlap=false,reject_trace=false,reject_break=false;
    double z=42,normal_z=1;
    bool operator()(unsigned stage,uint8_t* args){
        ++calls;
        if(!stage){
            uint64_t context=0;std::memcpy(&context,args,8);assert(context==0x10000);
            e33_surface_query::IgnoredActors ignored{};std::memcpy(&ignored,args+64,16);
            assert(ignored.num==1&&ignored.max==1&&ignored.data[0]==0x20000&&args[336]);
            args[376]=trace?1:0;args[88]=0x5a;return !reject_trace;
        }
        assert(args[0]==0x5a);args[248]=blocking?1:0;args[249]=overlap?1:0;
        const double point[]={10,20,z},normal[]={0,0,normal_z};
        std::memcpy(args+288,point,24);std::memcpy(args+336,normal,24);return !reject_break;
    }
};
int main(){
    const double start[]={10,20,100},end[]={10,20,-100};const uint64_t ignored[]={0x20000};
    e33_surface_query::Sample out{};
    auto run=[&](Fake& fake){return e33_surface_query::sample(fake,0x10000,start,end,ignored,1,out);};
    {Fake f;assert(run(f)==Result::Hit&&f.calls==2&&out.point[2]==42&&out.normal[2]==1);}
    {Fake f;f.trace=false;assert(run(f)==Result::NoHit&&f.calls==1&&out.point[2]==0);}
    {Fake f;f.overlap=true;assert(run(f)==Result::NoHit&&out.point[2]==0);}
    {Fake f;f.blocking=false;assert(run(f)==Result::NoHit);}
    {Fake f;f.normal_z=.74;assert(run(f)==Result::NoHit);}
    {Fake f;f.normal_z=.75;assert(run(f)==Result::Hit);}
    {Fake f;f.z=std::numeric_limits<double>::quiet_NaN();assert(run(f)==Result::Invalid);}
    {Fake f;f.normal_z=std::numeric_limits<double>::infinity();assert(run(f)==Result::Invalid);}
    {Fake f;f.reject_trace=true;assert(run(f)==Result::Rejected&&f.calls==1);}
    {Fake f;f.reject_break=true;assert(run(f)==Result::Rejected&&f.calls==2);}
    {Fake f;assert(e33_surface_query::sample(f,0,start,end,ignored,1,out)==Result::Invalid&&!f.calls);}
    {Fake f;assert(e33_surface_query::sample(f,0x10000,start,end,ignored,65,out)==Result::Invalid&&!f.calls);}
    {Fake f;const double bad[]={0,0,std::numeric_limits<double>::infinity()};assert(e33_surface_query::sample(f,0x10000,bad,end,ignored,1,out)==Result::Invalid&&!f.calls);}
}
