#include "npc_presentation_lifecycle.h"
#include "npc_interaction_isolation.h"
#include <cassert>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
using namespace e33_npc_presentation;
struct Ops {
    bool context=true,idle=true,admitted=true,retained=false,recorded=false,clean=true;
    std::string failure,exception;std::vector<std::string> calls;
    bool event(const char* name){calls.emplace_back(name);if(exception==name)throw std::runtime_error(name);return failure!=name;}
    bool current_context(){return context;}bool battle_quiescent(){return idle;}bool exact_original_admission(){return admitted;}
    bool allocate_once(){return event("allocate");}
    bool record_returned_actor(){const auto ok=event("record");recorded=ok;return ok;}
    bool retain_and_stabilize(){const auto ok=event("retain");retained=ok;return ok;}
    bool prepare_private_instance(){return event("prepare");}
    bool finish_original_construction(){return event("finish");}
    bool verify_original_identity_assembly_and_hold(){return event("verify-stage");}
    bool exact_owned_actor(){return recorded;}
    bool unregister_owned_interactions_once(){return event("unregister");}
    bool destroy_owned_actor_once(){return event("destroy");}
    bool verify_original_endplay_and_all_registrations_absent(){event("verify-cleanup");return clean;}
    bool release_owned_lease_once(){if(!retained)return true;const auto ok=event("release");if(ok)retained=false;return ok;}
};
struct IsolationOps : Ops {
    InteractionIsolationJournal journal{};
    bool enabled=true,ack=true;
    unsigned writes=0;
    InteractionIsolationIdentity owned_identity(){return {1,2,0x20000};}
    bool owns_identity(InteractionIsolationIdentity id){return retained&&id.index==1&&id.serial==2&&id.address==0x20000;}
    bool original_dialogue_contract(){return true;}
    bool interaction_flag_enabled(){return enabled;}
    bool assign_interaction_false_once(){++writes;enabled=false;return ack;}
    bool prepare_private_instance(){
        event("prepare");return isolate_owned_interaction(*this,journal)==InteractionIsolationResult::Complete;
    }
    bool verify_original_identity_assembly_and_hold(){
        event("verify-stage");return interaction_isolation_held(*this,journal);
    }
};
struct ConstructionResetOps : IsolationOps {
    InteractionIsolationJournal post{};
    bool post_ack=true;
    bool finish_original_construction(){
        event("finish");enabled=true;ack=post_ack;
        return isolate_owned_interaction(*this,post)==InteractionIsolationResult::Complete;
    }
    bool verify_original_identity_assembly_and_hold(){
        event("verify-stage");return interaction_isolation_held(*this,post);
    }
};
int main(){
    unsigned checks=0;
    {
        Lifecycle life;ConstructionResetOps ops;
        assert(life.stage(ops)==StageResult::Complete&&ops.writes==2&&ops.journal.verified&&ops.post.verified);
        assert(!ops.enabled&&life.retire(ops)==RetirementResult::Complete);
        assert(life.stage(ops)==StageResult::AlreadyAttempted&&ops.writes==2);++checks;
    }
    {
        Lifecycle life;ConstructionResetOps ops;ops.post_ack=false;
        assert(life.stage(ops)==StageResult::ConstructionIncomplete&&ops.writes==2&&ops.post.attempted&&!ops.post.verified);
        assert(life.retire(ops)==RetirementResult::Complete&&!ops.retained);
        assert(life.stage(ops)==StageResult::AlreadyAttempted&&ops.writes==2);++checks;
    }
    for(bool ack:{false,true}){
        Lifecycle life;IsolationOps ops;ops.ack=ack;
        assert(life.stage(ops)==(ack?StageResult::Complete:StageResult::ConstructionIncomplete));
        assert(ops.writes==1&&ops.journal.attempted);
        if(!ack)assert((ops.calls==std::vector<std::string>{"allocate","record","retain","prepare"}));
        // Even an unknown isolation acknowledgement cannot prevent retirement
        // of the exact retained actor or authorize replaying its construction.
        ops.enabled=true;
        assert(life.retire(ops)==RetirementResult::Complete&&!ops.retained);
        const auto calls=ops.calls;
        assert(life.stage(ops)==StageResult::AlreadyAttempted&&ops.writes==1&&ops.calls==calls);
        ++checks;
    }
    {
        Lifecycle life;Ops ops;assert(life.retire(ops)==RetirementResult::Complete);
        assert(life.stage(ops)==StageResult::AlreadyAttempted&&ops.calls.empty());++checks;
    }
    {
        Lifecycle life;Ops ops;assert(life.stage(ops)==StageResult::Complete);
        assert((ops.calls==std::vector<std::string>{"allocate","record","retain","prepare","finish","verify-stage"}));
        assert(life.retire(ops)==RetirementResult::Complete&&!ops.retained);
        const auto calls=ops.calls;assert(life.retire(ops)==RetirementResult::Complete&&ops.calls==calls);
        assert(life.stage(ops)==StageResult::AlreadyAttempted&&ops.calls==calls);++checks;
    }
    for(unsigned gate=0;gate<3;++gate){
        Lifecycle life;Ops ops;if(gate==0)ops.context=false;if(gate==1)ops.idle=false;if(gate==2)ops.admitted=false;
        assert(life.stage(ops)==StageResult::AdmissionRejected&&ops.calls.empty()&&!life.construction().attempted);++checks;
    }
    for(const auto* failure:{"allocate","record","retain","prepare","finish","verify-stage"}){
        Lifecycle life;Ops ops;ops.failure=failure;assert(life.stage(ops)==StageResult::ConstructionIncomplete);
        const auto calls=ops.calls;assert(life.stage(ops)==StageResult::AlreadyAttempted&&ops.calls==calls);
        assert(life.construction().attempted);++checks;
    }
    for(const auto* failure:{"retain","prepare","finish","verify-stage"}){
        Lifecycle life;Ops ops;ops.failure=failure;assert(life.stage(ops)==StageResult::ConstructionIncomplete&&ops.recorded);
        ops.failure.clear();assert(life.retire(ops)==RetirementResult::Complete&&!ops.retained);++checks;
    }
    for(const auto* failure:{"allocate","record"}){
        Lifecycle life;Ops ops;ops.failure=failure;assert(life.stage(ops)==StageResult::ConstructionIncomplete);
        const auto calls=ops.calls;assert(life.retire(ops)==RetirementResult::Deferred&&ops.calls==calls);
        assert(life.stage(ops)==StageResult::AlreadyAttempted&&ops.calls==calls);++checks;
    }
    {
        Lifecycle life;Ops ops;ops.exception="finish";try{life.stage(ops);assert(false);}catch(const std::runtime_error&){}
        assert(life.construction().phase==e33_owned_actor::ConstructionPhase::ConstructionPending&&ops.retained);
        ops.exception.clear();assert(life.stage(ops)==StageResult::AlreadyAttempted);
        assert(life.retire(ops)==RetirementResult::Complete);++checks;
    }
    for(unsigned gate=0;gate<3;++gate){
        Lifecycle life;Ops ops;assert(life.stage(ops)==StageResult::Complete);const auto calls=ops.calls;
        if(gate==0)ops.context=false;if(gate==1)ops.idle=false;if(gate==2)ops.recorded=false;
        assert(life.retire(ops)==RetirementResult::Deferred&&ops.calls==calls);++checks;
    }
    for(const auto* failure:{"unregister","destroy","release"}){
        Lifecycle life;Ops ops;assert(life.stage(ops)==StageResult::Complete);ops.failure=failure;
        assert(life.retire(ops)==RetirementResult::UnknownOutcome&&ops.retained);
        const auto calls=ops.calls;ops.failure.clear();assert(life.retire(ops)==RetirementResult::UnknownOutcome&&ops.calls==calls);++checks;
    }
    for(const auto* failure:{"unregister","destroy","release"}){
        Lifecycle life;Ops ops;assert(life.stage(ops)==StageResult::Complete);ops.exception=failure;
        try{life.retire(ops);assert(false);}catch(const std::runtime_error&){}
        const auto calls=ops.calls;ops.exception.clear();assert(life.retire(ops)==RetirementResult::UnknownOutcome&&ops.calls==calls&&ops.retained);++checks;
    }
    {
        Lifecycle life;Ops ops;assert(life.stage(ops)==StageResult::Complete);ops.clean=false;
        assert(life.retire(ops)==RetirementResult::Deferred&&ops.retained&&life.retirement()==RetirementPhase::Destroyed);
        const auto before=ops.calls.size();ops.clean=true;assert(life.retire(ops)==RetirementResult::Complete);
        assert(ops.calls.size()==before+2&&ops.calls[before]=="verify-cleanup"&&ops.calls.back()=="release");++checks;
    }
    std::cout<<checks<<" NPC lifecycle failure/order checks passed; no engine calls executed\n";
}
