#pragma once
#include "invocation_protocol.h"
namespace e33_enemy_spawn {
// Independent policy, context and arena proofs for another SDK-owned
// presentation. Defaults preserve the enemy path. Dispatch requires its own lifetime proof.
template<class Pool> struct ParameterInstanceAuthority {
    void* owner=nullptr;
    bool (*owns)(void*,uint64_t,uint64_t,Pool&,uint64_t,const CallIdentity&,uint64_t&)=nullptr;
    bool (*entry)(void*,uint64_t,uint64_t,Pool&,uint64_t,const CallIdentity&,const CallIdentity&,const CallIdentity&,uint64_t&)=nullptr;
    bool (*arena)(void*,uint64_t,uint64_t,Pool&,uint64_t,const CallIdentity&,CallIdentity&)=nullptr;
    bool (*copy_arena)(void*,uint64_t,uint64_t,Pool&,uint64_t,const CallIdentity&,const CallIdentity&,void*)=nullptr;
    bool (*dispatch)(void*,uint64_t,uint64_t,Pool&,uint64_t,const CallIdentity&,const CallIdentity&,const CallIdentity&)=nullptr;
    bool valid()const{return bool(owner)==bool(owns)&&(!(entry||arena||copy_arena)||owns)&&
        (!dispatch||(owns&&entry&&arena&&copy_arena));}
};
template<class Pool,class ExistingOwner> struct ParameterProofOwner {
    ExistingOwner& fallback;ParameterInstanceAuthority<Pool> authority;
    bool owned_instance_name(uint64_t b,uint64_t session,Pool& pool,uint64_t token,const CallIdentity& actor,uint64_t& name){
        if(!authority.valid())return false;
        return authority.owns?authority.owns(authority.owner,b,session,pool,token,actor,name):fallback.owned_instance_name(b,session,pool,token,actor,name);
    }
    bool owned_entry_context(uint64_t b,uint64_t session,Pool& pool,uint64_t token,const CallIdentity& actor,
            const CallIdentity& manager,const CallIdentity& function,uint64_t& name){
        if(!authority.valid())return false;
        if(!authority.owns)return fallback.owned_entry_context(b,session,pool,token,actor,manager,function,name);
        return authority.entry&&authority.entry(authority.owner,b,session,pool,token,actor,manager,function,name);
    }
    bool owned_entry_arena(uint64_t b,uint64_t session,Pool& pool,uint64_t token,const CallIdentity& actor,CallIdentity& arena){
        if(!authority.valid())return false;
        if(!authority.owns)return fallback.owned_entry_arena(b,session,pool,token,actor,arena);
        return authority.arena&&authority.arena(authority.owner,b,session,pool,token,actor,arena);
    }
    bool copy_entry_arena(uint64_t b,uint64_t session,Pool& pool,uint64_t token,const CallIdentity& actor,const CallIdentity& arena,void* to){
        if(!authority.valid())return false;
        if(!authority.owns)return fallback.copy_entry_arena(b,session,pool,token,actor,arena,to);
        return authority.copy_arena&&authority.copy_arena(authority.owner,b,session,pool,token,actor,arena,to);
    }
    bool note_entry_dispatch(uint64_t b,uint64_t session,Pool& pool,uint64_t token,const CallIdentity& actor,const CallIdentity& manager,const CallIdentity& function){
        if(!authority.valid())return false;
        if(authority.owns)return authority.dispatch&&authority.dispatch(authority.owner,b,session,pool,token,actor,manager,function);
        return fallback.note_entry_dispatch(b,session,pool,token,actor,manager,function);
    }
};
}
