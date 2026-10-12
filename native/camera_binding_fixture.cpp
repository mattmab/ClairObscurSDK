#include "bound_camera_proof.h"
#include "bound_object_frame.h"
#include <cassert>
#include <iostream>
#include <stdexcept>
using namespace e33_camera_binding;
struct QueryOps {
    bool live=true,valid=true,hold=true,released=true,throw_dispatch=false,throw_free=false,mutate=false;
    int count=1,capacity=1,dispatches=0,frees=0,retains=0;uint64_t values[8]{42};
    bool context(){return live;}bool validate(const BindingValue&){return valid;}
    void dispatch(void* args){++dispatches;if(throw_dispatch)throw std::runtime_error("dispatch");
        ObjectArray header{capacity?reinterpret_cast<uint64_t>(values):0,count,capacity};
        std::memcpy(static_cast<char*>(args)+24,&header,16);if(mutate)*static_cast<char*>(args)^=1;}
    bool read_pointer(uint64_t at,uint64_t& out){std::memcpy(&out,reinterpret_cast<void*>(at),8);return true;}
    bool capture(uint64_t object,uint64_t& id){id=object;return true;}
    bool same(uint64_t a,uint64_t b){return a==b;}
    bool retain(uint64_t&){++retains;return hold;}
    void free_array(uint64_t){++frees;if(throw_free)throw std::runtime_error("free");}
    bool outputs_released(){return released;}
};
struct ProofOps {
    bool live=true,profile=true,association=true,overrides_empty=true,bound=true,spawn=true,hold=true,identity=true,empty=true;
    uint64_t selected=42;int queries=0;
    bool context(){return live;}bool profile_asset(Profile,uint64_t asset){return profile&&asset==2;}
    bool owned_player_asset(uint64_t p,uint64_t a){return association&&p==1&&a==2;}
    bool no_overrides(uint64_t){return overrides_empty;}
    bool single_bound_camera(uint64_t,uint64_t,const Guid&,uint64_t& camera){++queries;camera=selected;return bound;}
    bool spawned_by_player(uint64_t,uint64_t,const Guid&,uint64_t){return spawn;}
    bool same(uint64_t a,uint64_t b){return a==b;}bool retain(uint64_t&){return hold;}
    bool valid(uint64_t){return identity;}bool held(uint64_t){return hold;}bool holds_empty(){return empty;}
};
int main(){
    BindingValue binding{{3868951513u,1230066568u,4000387518u,2702779930u},0,0};
    // Binding integer values here are synthetic; fixture does not establish their runtime semantics.
    {QueryOps o;BoundObjectFrame<uint64_t> f;assert(f.query(o,binding)==QueryResult::ok);assert(f.count()==1&&f.identities()[0]==42&&o.frees==1);assert(f.reset(o));}
    {QueryOps o;o.count=o.capacity=0;BoundObjectFrame<uint64_t> f;assert(f.query(o,binding)==QueryResult::empty);assert(o.frees==0);}
    {QueryOps o;o.capacity=65;BoundObjectFrame<uint64_t> f;assert(f.query(o,binding)==QueryResult::unknown);assert(o.retains==0&&o.frees==0);}
    {QueryOps o;o.count=2;o.capacity=2;o.values[1]=42;BoundObjectFrame<uint64_t> f;assert(f.query(o,binding)==QueryResult::unknown);assert(f.quarantined());}
    {QueryOps o;o.throw_dispatch=true;BoundObjectFrame<uint64_t> f;try{f.query(o,binding);assert(false);}catch(const std::runtime_error&){}assert(f.quarantined()&&!f.reset(o));}
    {QueryOps o;o.throw_free=true;BoundObjectFrame<uint64_t> f;try{f.query(o,binding);assert(false);}catch(const std::runtime_error&){}assert(f.quarantined()&&!f.reset(o));}
    {QueryOps o;o.mutate=true;BoundObjectFrame<uint64_t> f;assert(f.query(o,binding)==QueryResult::unknown);}
    {QueryOps o;o.hold=false;BoundObjectFrame<uint64_t> f;assert(f.query(o,binding)==QueryResult::unknown);assert(o.frees==0);}
    {QueryOps o;o.valid=false;BoundObjectFrame<uint64_t> f;assert(f.query(o,binding)==QueryResult::rejected);assert(o.dispatches==0);}
    Guid guid{{3868951513u,1230066568u,4000387518u,2702779930u}},other{{1,2,3,4}};
    {ProofOps o;Proof<uint64_t> p;assert(p.begin(o,7,Profile::locomotive,1,2));assert(!p.admit(o,8,guid));assert(!p.admit(o,7,other));assert(o.queries==0);
     assert(p.admit(o,7,guid));assert(p.matches(o,7,1,42));assert(!p.matches(o,8,1,42));assert(!p.matches(o,7,3,42));assert(!p.matches(o,7,1,43));
     o.overrides_empty=false;assert(!p.matches(o,7,1,42));o.overrides_empty=true;o.hold=false;assert(!p.matches(o,7,1,42));}
    {ProofOps o;o.spawn=false;Proof<uint64_t> p;p.begin(o,7,Profile::locomotive,1,2);assert(!p.admit(o,7,guid));assert(p.count()==0);}
    {ProofOps o;o.hold=false;Proof<uint64_t> p;p.begin(o,7,Profile::locomotive,1,2);assert(!p.admit(o,7,guid));assert(p.quarantined());}
    {ProofOps o;Proof<uint64_t> p;p.begin(o,7,Profile::locomotive,1,2);assert(p.admit(o,7,guid));assert(!p.admit(o,7,guid));o.empty=false;assert(!p.released(o));o.empty=true;assert(p.released(o));assert(!p.matches(o,7,1,42));}
    std::cout<<"Bound array lifecycle and camera proof fixtures passed\n";
}
