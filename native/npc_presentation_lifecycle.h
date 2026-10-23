#pragma once
#include "owned_actor_construction.h"
#include "owned_actor_retirement.h"

// NPC-specific sequencing only. An engine bridge must separately prove exact
// admitted classes, current world/controller, original unavailable override,
// unique original-construction GUID, complete interaction/listener cleanup and
// strong lease ownership. This helper grants no engine or class authority.
namespace e33_npc_presentation {
enum class StageResult { Complete, AdmissionRejected, AlreadyAttempted, ConstructionIncomplete };
using RetirementPhase=e33_owned_actor::RetirementPhase;
using RetirementResult=e33_owned_actor::RetirementResult;

class Lifecycle {
    e33_owned_actor::ConstructionJournal construction_{};
    RetirementPhase retirement_=RetirementPhase::Ready;
public:
    const e33_owned_actor::ConstructionJournal& construction()const{return construction_;}
    RetirementPhase retirement()const{return retirement_;}
    template<class Ops> StageResult stage(Ops& ops){
        if(construction_.attempted||retirement_!=RetirementPhase::Ready)return StageResult::AlreadyAttempted;
        if(!ops.current_context()||!ops.battle_quiescent()||!ops.exact_original_admission())return StageResult::AdmissionRejected;
        const auto result=e33_owned_actor::construct(construction_,
            [&](){return ops.allocate_once();},
            [&](){return ops.record_returned_actor();},
            [&](){return ops.retain_and_stabilize();},
            [&](){return ops.prepare_private_instance();},
            [&](){return ops.finish_original_construction();},
            [&](){return ops.verify_original_identity_assembly_and_hold();});
        return result==e33_owned_actor::ConstructionResult::Complete?StageResult::Complete:StageResult::ConstructionIncomplete;
    }
    template<class Ops> RetirementResult retire(Ops& ops){
        return e33_owned_actor::retire(retirement_,construction_.attempted,ops);
    }
};
}
