#include "map_runtime_readiness.h"
#include <cassert>
#include <limits>
struct Fake {
    unsigned calls=0;bool reject=false,missing=false,steep=false,overlap=false,far=false;
    bool operator()(unsigned stage,uint8_t* args){
        ++calls;if(reject)return false;
        if(!stage){args[376]=missing?0:1;return true;}
        args[248]=1;args[249]=overlap?1:0;
        const double point[]={0,0,far?-1000.:100.},normal[]={0,0,steep?.5:1.};
        std::memcpy(args+288,point,24);std::memcpy(args+336,normal,24);
        const uint64_t actor=111,component=222;std::memcpy(args+368,&actor,8);std::memcpy(args+376,&component,8);return true;
    }
};
int main(){
    const double center[]={0,0,200.};e33_map_readiness::Support out{};
    const auto owned=[](uint64_t a,uint64_t c){return a==111&&c==222;};
    {Fake f;assert(e33_map_readiness::support(f,owned,7,center,40,100,out));assert(out.samples==5&&out.hits==5&&out.owned==5&&f.calls==10);}
    {Fake f;f.reject=true;assert(!e33_map_readiness::support(f,owned,7,center,40,100,out));assert(out.samples==1&&!out.hits);}
    {Fake f;f.missing=true;assert(e33_map_readiness::support(f,owned,7,center,40,100,out));assert(out.samples==5&&!out.hits);}
    {Fake f;f.steep=true;assert(e33_map_readiness::support(f,owned,7,center,40,100,out));assert(!out.hits);}
    {Fake f;f.overlap=true;assert(e33_map_readiness::support(f,owned,7,center,40,100,out));assert(!out.hits);}
    {Fake f;f.far=true;assert(e33_map_readiness::support(f,owned,7,center,40,100,out));assert(!out.hits);}
    {Fake f;assert(!e33_map_readiness::support(f,owned,7,center,101,100,out));assert(!f.calls);}
    {Fake f;assert(e33_map_readiness::support(f,[](uint64_t,uint64_t){return false;},7,center,40,100,out));assert(out.hits==5&&!out.owned);}
}
