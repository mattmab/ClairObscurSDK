#include "npc_dialogue_availability_body.h"
#include "npc_dialogue_availability_fixture.h"
#include "npc_interaction_isolation.h"
#include "npc_dialogue_local_schema.h"
#include <cassert>
#include <iostream>
using namespace e33_npc_presentation;
struct FakeOps {
    bool owned=true,contract=true,enabled=true,ack=true,change_identity=false;
    unsigned writes=0;
    InteractionIsolationIdentity identity{1,2,0x20000};
    InteractionIsolationIdentity owned_identity(){return identity;}
    bool owns_identity(InteractionIsolationIdentity observed){
        return owned&&observed.index==identity.index&&observed.serial==identity.serial&&observed.address==identity.address;
    }
    bool original_dialogue_contract(){return contract;}
    bool interaction_flag_enabled(){return enabled;}
    bool assign_interaction_false_once(){
        ++writes;enabled=false;
        if(change_identity)++identity.serial;
        return ack;
    }
};
int main(){
    // Original metadata captured in curator-inherited-availability-script-v162.json.
    constexpr uint64_t base=0x7ff62ef50000,function=0x207730e05c0;
    const uint32_t observed_numbers[]={0,0,0,0,0,2,3};
    for(unsigned ordinal=0;ordinal<7;++ordinal){
        const DialogueLocalSchema original{base+0x6e119b0,function|1,
            ordinal?0x8001040000200ULL:0x8001040000380ULL,
            observed_numbers[ordinal],1,1,ordinal,0xff010001};
        assert(dialogue_local_schema(original,ordinal,base,function));
        assert(!dialogue_local_schema(original,7,base,function));
        for(unsigned member=0;member<8;++member){
            auto bad=original;
            switch(member){
                case 0:bad.table^=8;break;case 1:bad.owner^=8;break;
                case 2:bad.flags^=1;break;case 3:bad.number^=1;break;
                case 4:bad.dimension=2;break;case 5:bad.width=2;break;
                case 6:bad.offset^=1;break;case 7:bad.boolean^=1;break;
            }
            assert(!dialogue_local_schema(bad,ordinal,base,function));
        }
    }
    const auto& bytes=npc_dialogue_fixture::bytes;
    const auto& refs=npc_dialogue_fixture::refs;
    assert(dialogue_availability_body(bytes.data(),bytes.size(),refs));
    assert(!dialogue_availability_body(nullptr,bytes.size(),refs));
    assert(!dialogue_availability_body(bytes.data(),bytes.size()-1,refs));
    for(size_t i=0;i<bytes.size();++i){
        auto changed=bytes;changed[i]^=1;
        assert(!dialogue_availability_body(changed.data(),changed.size(),refs));
    }
    for(size_t i=0;i<refs.size();++i){
        auto changed=refs;changed[i]^=0x10000;
        assert(!dialogue_availability_body(bytes.data(),bytes.size(),changed));
    }
    auto aliases=refs;aliases[1]=aliases[0];
    assert(!dialogue_availability_body(bytes.data(),bytes.size(),aliases));
    FakeOps good;InteractionIsolationJournal complete;
    assert(isolate_owned_interaction(good,complete)==InteractionIsolationResult::Complete);
    assert(good.writes==1&&interaction_isolation_held(good,complete));
    assert(isolate_owned_interaction(good,complete)==InteractionIsolationResult::AlreadyAttempted);
    assert(good.writes==1);
    good.enabled=true;assert(!interaction_isolation_held(good,complete));
    good.enabled=false;++good.identity.serial;assert(!interaction_isolation_held(good,complete));
    for(unsigned failure=0;failure<3;++failure){
        FakeOps rejected;InteractionIsolationJournal journal;
        if(failure==0)rejected.owned=false;
        if(failure==1)rejected.contract=false;
        if(failure==2)rejected.enabled=false;
        assert(isolate_owned_interaction(rejected,journal)==InteractionIsolationResult::Rejected);
        assert(!journal.attempted&&rejected.writes==0&&!interaction_isolation_held(rejected,journal));
    }
    for(bool identity_change:{false,true}){
        FakeOps unknown;unknown.ack=identity_change;unknown.change_identity=identity_change;
        InteractionIsolationJournal journal;
        assert(isolate_owned_interaction(unknown,journal)==InteractionIsolationResult::UnknownOutcome);
        assert(!interaction_isolation_held(unknown,journal));
        assert(isolate_owned_interaction(unknown,journal)==InteractionIsolationResult::AlreadyAttempted);
        assert(unknown.writes==1);
    }
    std::cout<<"Seven local schemas, 56 schema mutations, complete body, 232 byte mutations, 15 reference mutations, ownership and once-only isolation checks passed\n";
}
