#include "authored_binding_query_authority.h"
#include <cassert>

using namespace e33_camera_binding;
using e33_authored_binding::Authority;
struct Identity {uint64_t value=0;};
struct Resolver {
    bool stable=true,owned=true,reachable=true,authored=true,released=true;
    QueryResult outcome=QueryResult::ok;
    unsigned calls=0;
    bool context()const{return stable;}
    bool same(Identity a,Identity b)const{return a.value==b.value;}
    bool owned_player(uint64_t s,Identity p,Identity a,Identity root)const {
        return owned && s==7 && p.value==10 && a.value==20 && root.value==30;
    }
    bool unique_reachable_source(uint64_t s,Identity root,Identity source)const {
        return reachable && s==7 && root.value==30 && source.value==40;
    }
    bool authored_binding(uint64_t s,Identity source,const uint32_t (&guid)[4])const {
        return authored && s==7 && source.value==40 && guid[0]==1 && guid[1]==2 && guid[2]==3 && guid[3]==4;
    }
    bool outputs_released()const{return released;}
    QueryResult resolve(uint64_t,Identity,Identity,const uint32_t (&guid)[4],BindingValue& out) {
        ++calls;std::memcpy(out.guid,guid,sizeof(out.guid));out.sequence_id=155498434;out.resolve_parent_index=0;
        return outcome;
    }
};
struct Reader {
    Resolver& resolver;Authority<Identity>& authority;
    uint64_t data[2]{101,102};unsigned retained=0,freed=0;
    bool active_override=true;
    bool oversized=false,change_owner=false;
    bool context()const{return resolver.context();}
    bool validate(const BindingValue& binding)const {
        // Active overrides must not preclude an owned-player read.
        return active_override && authority.matches(resolver,7,{10},{20},{30},binding);
    }
    void dispatch(void* frame) {
        auto* result=reinterpret_cast<ObjectArray*>(static_cast<uint8_t*>(frame)+sizeof(BindingValue));
        *result={reinterpret_cast<uint64_t>(data),oversized?9:2,oversized?9:2};
        if(change_owner)resolver.owned=false;
    }
    bool read_pointer(uint64_t address,uint64_t& value)const {
        std::memcpy(&value,reinterpret_cast<void*>(address),sizeof(value));return true;
    }
    bool capture(uint64_t object,Identity& result)const {result={object};return object!=0;}
    bool same(Identity a,Identity b)const{return a.value==b.value;}
    bool retain(Identity&) {++retained;return true;}
    void free_array(uint64_t) {++freed;}
    bool outputs_released()const{return retained==0;}
};
int main() {
    constexpr uint32_t child[4]{1,2,3,4};
    Resolver resolver;Authority<Identity> authority;
    assert(authority.derive(resolver,7,{10},{20},{30},{40},child));
    BindingValue nested{{1,2,3,4},155498434,0};
    assert(authority.matches(resolver,7,{10},{20},{30},nested));
    auto altered=nested;altered.sequence_id=0;
    assert(!authority.matches(resolver,7,{10},{20},{30},altered));
    altered=nested;altered.resolve_parent_index=-1;
    assert(!authority.matches(resolver,7,{10},{20},{30},altered));
    altered=nested;altered.guid[0]=9;
    assert(!authority.matches(resolver,7,{10},{20},{30},altered));
    resolver.owned=false;assert(!authority.matches(resolver,7,{10},{20},{30},nested));resolver.owned=true;
    resolver.authored=false;assert(!authority.matches(resolver,7,{10},{20},{30},nested));resolver.authored=true;
    Reader reader{resolver,authority};BoundObjectFrame<Identity> query;
    assert(query.query(reader,nested)==QueryResult::ok);
    assert(query.count()==2 && query.identities()[0].value==101 && query.identities()[1].value==102);
    assert(reader.retained==2 && reader.freed==1);
    assert(!query.reset(reader));reader.retained=0;assert(query.reset(reader));
    Reader malformed{resolver,authority};malformed.oversized=true;BoundObjectFrame<Identity> bad;
    assert(bad.query(malformed,nested)==QueryResult::unknown && bad.quarantined());
    assert(bad.query(malformed,nested)==QueryResult::rejected && malformed.freed==0);
    Reader stale{resolver,authority};stale.change_owner=true;BoundObjectFrame<Identity> changed;
    assert(changed.query(stale,nested)==QueryResult::unknown && changed.quarantined());
    resolver.owned=true;
    assert(authority.clear(resolver));
    Resolver uncertain;uncertain.outcome=QueryResult::unknown;Authority<Identity> tainted;
    assert(!tainted.derive(uncertain,7,{10},{20},{30},{40},child));
    assert(tainted.uncertain() && !tainted.clear(uncertain));
    assert(!tainted.derive(uncertain,7,{10},{20},{30},{40},child) && uncertain.calls==1);
    Resolver rejected;rejected.outcome=QueryResult::rejected;Authority<Identity> retriable;
    assert(!retriable.derive(rejected,7,{10},{20},{30},{40},child));
    assert(!retriable.uncertain());rejected.outcome=QueryResult::ok;
    assert(retriable.derive(rejected,7,{10},{20},{30},{40},child));
    Resolver forged;forged.authored=false;Authority<Identity> denied;
    assert(!denied.derive(forged,7,{10},{20},{30},{40},child) && forged.calls==0 && !denied.uncertain());
    assert(denied.rejection_stage()==4);
    Resolver no_owner;no_owner.owned=false;Authority<Identity> owner_denied;
    assert(!owner_denied.derive(no_owner,7,{10},{20},{30},{40},child) && owner_denied.rejection_stage()==2);
    Resolver no_source;no_source.reachable=false;Authority<Identity> source_denied;
    assert(!source_denied.derive(no_source,7,{10},{20},{30},{40},child) && source_denied.rejection_stage()==3);
    assert(retriable.rejection_stage()==0);
}
