#include "parameter_instance_authority.h"
#include <cassert>
#include <cstdio>
using namespace e33_enemy_spawn;
struct Pool {};
struct Fallback {
    unsigned calls=0;
    bool owned_instance_name(uint64_t,uint64_t,Pool&,uint64_t,const CallIdentity&,uint64_t& name){++calls;name=11;return true;}
    bool owned_entry_context(uint64_t,uint64_t,Pool&,uint64_t,const CallIdentity&,const CallIdentity&,const CallIdentity&,uint64_t& name){++calls;name=11;return true;}
    bool owned_entry_arena(uint64_t,uint64_t,Pool&,uint64_t,const CallIdentity&,CallIdentity&){++calls;return true;}
    bool copy_entry_arena(uint64_t,uint64_t,Pool&,uint64_t,const CallIdentity&,const CallIdentity&,void* to){++calls;*static_cast<int*>(to)=33;return true;}
    bool note_entry_dispatch(uint64_t,uint64_t,Pool&,uint64_t,const CallIdentity&,const CallIdentity&,const CallIdentity&){++calls;return true;}
};
struct Checks {
    unsigned calls=0;bool fail=false;uint64_t token=0;
    static bool owns(void* p,uint64_t,uint64_t,Pool&,uint64_t token,const CallIdentity&,uint64_t& name){
        auto& c=*static_cast<Checks*>(p);++c.calls;c.token=token;name=22;return !c.fail;
    }
    static bool entry(void* p,uint64_t b,uint64_t s,Pool& pool,uint64_t token,const CallIdentity& actor,const CallIdentity&,const CallIdentity&,uint64_t& name){
        return owns(p,b,s,pool,token,actor,name);
    }
    static bool dispatch(void* p,uint64_t b,uint64_t s,Pool& pool,uint64_t token,const CallIdentity& actor,const CallIdentity&,const CallIdentity&){
        uint64_t name=0;return owns(p,b,s,pool,token,actor,name);
    }
    static bool arena(void* p,uint64_t b,uint64_t s,Pool& pool,uint64_t token,const CallIdentity& actor,CallIdentity& out){
        uint64_t name=0;out={1,2,0x10000};return owns(p,b,s,pool,token,actor,name);
    }
    static bool copy(void* p,uint64_t b,uint64_t s,Pool& pool,uint64_t token,const CallIdentity& actor,const CallIdentity&,void* to){
        uint64_t name=0;if(!owns(p,b,s,pool,token,actor,name))return false;*static_cast<int*>(to)=55;return true;
    }
};
int main(){
    Pool pool;CallIdentity actor{1,2,0x10000},arena{};uint64_t name=0;int target=0;
    {Fallback fallback;ParameterProofOwner<Pool,Fallback> p{fallback,{}};
     assert(p.owned_instance_name(1,2,pool,42,actor,name)&&name==11);
     assert(p.owned_entry_context(1,2,pool,42,actor,actor,actor,name));assert(p.owned_entry_arena(1,2,pool,42,actor,arena));
     assert(p.copy_entry_arena(1,2,pool,42,actor,arena,&target)&&target==33);
     assert(p.note_entry_dispatch(1,2,pool,42,actor,actor,actor)&&fallback.calls==5);}
    {Fallback fallback;Checks checks;ParameterProofOwner<Pool,Fallback> p{fallback,{&checks,Checks::owns}};
     assert(p.owned_instance_name(1,2,pool,42,actor,name)&&name==22&&checks.token==42);
     assert(!p.owned_entry_context(1,2,pool,42,actor,actor,actor,name));assert(!p.owned_entry_arena(1,2,pool,42,actor,arena));
     assert(!p.copy_entry_arena(1,2,pool,42,actor,arena,&target));assert(!p.note_entry_dispatch(1,2,pool,42,actor,actor,actor));
     assert(checks.calls==1&&fallback.calls==0);}
    {Fallback fallback;Checks checks;ParameterProofOwner<Pool,Fallback> p{fallback,{&checks,Checks::owns,Checks::entry,Checks::arena,Checks::copy}};
     assert(p.owned_instance_name(1,2,pool,42,actor,name));assert(p.owned_entry_context(1,2,pool,42,actor,actor,actor,name));
     assert(p.owned_entry_arena(1,2,pool,42,actor,arena));assert(p.copy_entry_arena(1,2,pool,42,actor,arena,&target)&&target==55);
     assert(!p.note_entry_dispatch(1,2,pool,42,actor,actor,actor)&&checks.calls==4&&fallback.calls==0);
     checks.fail=true;assert(!p.owned_entry_context(1,2,pool,42,actor,actor,actor,name)&&fallback.calls==0);}
    {Fallback fallback;Checks checks;ParameterProofOwner<Pool,Fallback> p{fallback,
        {&checks,Checks::owns,Checks::entry,Checks::arena,Checks::copy,Checks::dispatch}};
     assert(p.note_entry_dispatch(1,2,pool,42,actor,actor,actor)&&checks.token==42&&checks.calls==1);
     checks.fail=true;assert(!p.note_entry_dispatch(1,2,pool,42,actor,actor,actor)&&fallback.calls==0);}
    for(unsigned i=0;i<4;++i){
        Fallback fallback;Checks checks;ParameterInstanceAuthority<Pool> authority{};
        if(i==0)authority.owner=&checks;
        if(i==1)authority.owns=Checks::owns;
        if(i==2)authority.entry=Checks::entry;
        if(i==3){authority.owner=&checks;authority.owns=Checks::owns;authority.dispatch=Checks::dispatch;}
        ParameterProofOwner<Pool,Fallback> p{fallback,authority};
        assert(!authority.valid());assert(!p.owned_instance_name(1,2,pool,42,actor,name));
        assert(!p.owned_entry_context(1,2,pool,42,actor,actor,actor,name));assert(!p.owned_entry_arena(1,2,pool,42,actor,arena));
        assert(!p.copy_entry_arena(1,2,pool,42,actor,arena,&target));assert(!p.note_entry_dispatch(1,2,pool,42,actor,actor,actor));
        assert(fallback.calls==0&&checks.calls==0);
    }
    std::puts("Parameter authority: fallback preserved; independent proofs, rejection, dispatch denial and explicit lifetime callback passed");
}
