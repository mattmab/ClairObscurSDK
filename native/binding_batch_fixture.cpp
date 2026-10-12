#include "binding_query_batch.h"
#include "binding_override_header.h"
#include <cassert>
#include <stdexcept>
#include <iostream>
using namespace e33_camera_binding;
struct FakeQuery {
    bool live=true,valid=true,throw_read=false,throw_dispatch=false,throw_free=false;
    int count=1,capacity=1;
    uint32_t dispatches=0,frees=0,held=0;
    uint64_t values[8]{100,101};
    bool context()const{return live;}
    bool validate(const BindingValue& binding)const {
        Guid guid{};std::memcpy(guid.words,binding.guid,16);
        return valid && binding.sequence_id==0 && binding.resolve_parent_index==-1 &&
            (allowed(Profile::locomotive,guid)||allowed(Profile::scavenger,guid));
    }
    void dispatch(void* args) {
        ++dispatches;if(throw_dispatch)throw std::runtime_error("dispatch");
        values[0]=100+dispatches;
        ObjectArray header{capacity ? reinterpret_cast<uint64_t>(values):0,count,capacity};
        std::memcpy(static_cast<char*>(args)+24,&header,16);
    }
    bool read_pointer(uint64_t at,uint64_t& out)const {if(throw_read)throw std::runtime_error("read");std::memcpy(&out,reinterpret_cast<void*>(at),8);return true;}
    bool capture(uint64_t object,uint64_t& id)const{id=object;return true;}
    bool same(uint64_t a,uint64_t b)const{return a==b;}
    bool retain(uint64_t&){++held;return true;}
    void free_array(uint64_t){++frees;if(throw_free)throw std::runtime_error("free");}
    bool outputs_released()const{return held==0;}
};
struct FakeOwner {
    FakeQuery query;
    uint32_t proofs=0,release_calls=0,prepared=0,proof_releases=0;
    bool deferred=false,adopt_ok=true,throw_adopt=false,uncertain_adopt=false,empty_matches=true;
    bool context()const{return query.live;}
    FakeQuery& query_ops(){return query;}
    bool prepare_outputs(){++prepared;return true;}
    AdoptionResult empty_binding(const Guid&){return empty_matches ? AdoptionResult::ok:AdoptionResult::rejected;}
    AdoptionResult adopt(const Guid&,uint64_t) {if(throw_adopt)throw std::runtime_error("adopt");if(!adopt_ok)return AdoptionResult::rejected;++proofs;return uncertain_adopt ? AdoptionResult::unknown:AdoptionResult::ok;}
    QueryResult release_outputs(){++release_calls;if(deferred)return QueryResult::deferred;query.held=0;return QueryResult::ok;}
    QueryResult release_proofs(){++proof_releases;proofs=0;return QueryResult::ok;}
};
int main() {
    {FactoryOverrideState state{};
     assert(factory_override_lookup_empty(state));state.dirty=1;assert(factory_override_lookup_empty(state));
     for(int which=0;which<7;++which) {
      auto bad=state;
      switch(which) {case 0:bad.bindings.data=0x1000;break;case 1:bad.bindings.count=1;break;
       case 2:bad.bindings.capacity=1;break;case 3:bad.sparse_count=1;break;case 4:bad.free_count=1;break;
       case 5:bad.hash_size=1;break;case 6:bad.dirty=2;break;}
      assert(!factory_override_lookup_empty(bad));}
     state.sparse_count=-1;assert(!factory_override_lookup_empty(state));state={};state.free_count=-1;
     assert(!factory_override_lookup_empty(state));state={};state.hash_size=-1;assert(!factory_override_lookup_empty(state));}
    assert(empty_override_array({0,0,0}));
    assert(empty_override_array({0x1000,0,1}));
    assert(!empty_override_array({0,0,1}));
    assert(!empty_override_array({0x1000,0,0}));
    assert(!empty_override_array({0x1001,0,1}));
    assert(!empty_override_array({0x1000,1,1}));
    assert(!empty_override_array({0x1000,-1,1}));
    assert(!empty_override_array({0x1000,0,-1}));
    assert(!empty_override_array({0x1000,0,65}));
    assert(!empty_override_array({UINT64_MAX-7,0,1}));
    // Same batch/frame implementation instantiated by SequenceBindingQueryOwner.
    {FakeOwner o;BindingQueryBatch<uint64_t> b;assert(b.begin(Profile::scavenger));
     assert(b.run(o)==QueryResult::ok);assert(b.completed()==5&&b.matched()==5&&b.outcome()==1);
     assert(o.query.dispatches==5&&o.query.frees==5&&o.proofs==5&&o.query.held==0);
     assert(b.run(o)==QueryResult::ok&&o.query.dispatches==5);
     assert(b.close(o)==QueryResult::ok&&o.proofs==0&&o.proof_releases==1);assert(b.begin(Profile::locomotive));}
    {FakeOwner o;o.query.count=o.query.capacity=0;BindingQueryBatch<uint64_t> b;b.begin(Profile::scavenger);
     assert(b.run(o)==QueryResult::ok&&b.completed()==5&&b.matched()==0&&o.query.frees==0);assert(b.close(o)==QueryResult::ok);}
    {FakeOwner o;o.query.count=o.query.capacity=0;o.empty_matches=false;BindingQueryBatch<uint64_t> b;b.begin(Profile::scavenger);
     assert(b.run(o)==QueryResult::rejected&&b.completed()==1&&b.matched()==0&&!b.uncertain());assert(b.close(o)==QueryResult::ok);}
    {FakeOwner o;o.deferred=true;BindingQueryBatch<uint64_t> b;b.begin(Profile::locomotive);
     assert(b.run(o)==QueryResult::deferred&&o.query.dispatches==1&&o.proofs==1&&o.query.held==1);
     assert(b.close(o)==QueryResult::deferred);o.deferred=false;assert(b.close(o)==QueryResult::ok&&o.query.dispatches==1&&o.proofs==0);}
    {FakeOwner o;o.query.valid=false;BindingQueryBatch<uint64_t> b;b.begin(Profile::locomotive);
     assert(b.run(o)==QueryResult::rejected&&o.query.dispatches==0&&b.outcome()==0);assert(b.close(o)==QueryResult::ok);}
    {FakeOwner o;o.query.count=o.query.capacity=2;o.query.values[1]=999;BindingQueryBatch<uint64_t> b;b.begin(Profile::locomotive);
     assert(b.run(o)==QueryResult::rejected&&b.completed()==1&&b.matched()==0&&o.query.frees==1&&o.query.held==0);assert(b.close(o)==QueryResult::ok);}
    for(int fault=0;fault<4;++fault) {FakeOwner o;o.query.throw_dispatch=fault==0;o.query.throw_read=fault==1;
     o.query.throw_free=fault==2;o.throw_adopt=fault==3;BindingQueryBatch<uint64_t> b;b.begin(Profile::locomotive);
     try{b.run(o);assert(false);}catch(const std::runtime_error&){}
     const auto dispatched=o.query.dispatches,freed=o.query.frees;
     assert(b.uncertain()&&b.close(o)==QueryResult::unknown&&b.run(o)==QueryResult::unknown);
     assert(o.query.dispatches==dispatched&&o.query.frees==freed&&o.proof_releases==0);}
    {FakeOwner o;o.adopt_ok=false;BindingQueryBatch<uint64_t> b;b.begin(Profile::locomotive);
     assert(b.run(o)==QueryResult::rejected&&!b.uncertain()&&b.completed()==1&&b.matched()==0&&o.proofs==0&&o.query.held==0);
     assert(b.close(o)==QueryResult::ok);}
    {FakeOwner o;o.uncertain_adopt=true;BindingQueryBatch<uint64_t> b;b.begin(Profile::locomotive);
     assert(b.run(o)==QueryResult::unknown&&b.uncertain()&&o.proofs==1&&b.close(o)==QueryResult::unknown);}
    std::cout<<"Authored binding batch query/cleanup fixtures passed\n";
}
