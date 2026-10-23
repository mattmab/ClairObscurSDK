#include "owned_actor_construction.h"
#include <stdexcept>
#include <vector>
using namespace e33_owned_actor;

int main() {
    // An acknowledgement failure at each boundary must retain the pending
    // phase and prevent replay. Later callbacks (including FinishSpawning)
    // must not run after a failure in identity, retention or preparation.
    const ConstructionPhase pending[]={ConstructionPhase::AllocationPending,
        ConstructionPhase::IdentityPending,ConstructionPhase::RetentionPending,
        ConstructionPhase::PreparationPending,ConstructionPhase::ConstructionPending,
        ConstructionPhase::FinalizationPending};
    const ConstructionResult failures[]={ConstructionResult::AllocationFailed,
        ConstructionResult::IdentityFailed,ConstructionResult::RetentionFailed,
        ConstructionResult::PreparationFailed,ConstructionResult::ConstructionFailed,
        ConstructionResult::FinalizationFailed};
    for(int failure=-1;failure<6;++failure) {
        ConstructionJournal journal;std::vector<int> calls;bool recorded=false,leased=false;
        auto step=[&](int index){
            calls.push_back(index);
            if(index>=2&&!recorded)throw std::logic_error("Actor not recorded before fallible retention");
            if(index>=3&&!leased)throw std::logic_error("Unretained actor reached engine setup");
            if(index==failure)return false;
            if(index==1)recorded=true;
            if(index==2)leased=true;
            return true;
        };
        auto run=[&](){return construct(journal,[&](){return step(0);},[&](){return step(1);},
            [&](){return step(2);},[&](){return step(3);},[&](){return step(4);},[&](){return step(5);});};
        const auto result=run();
        if(failure<0) {
            if(result!=ConstructionResult::Complete||journal.phase!=ConstructionPhase::Complete||calls.size()!=6)return 1;
        } else if(result!=failures[failure]||journal.phase!=pending[failure]||calls.size()!=size_t(failure+1))return 2;
        const auto count=calls.size();
        if(!journal.attempted||run()!=ConstructionResult::AlreadyAttempted||calls.size()!=count)return 3;
    }
    // Unknown outcomes are not resumable. Exceptions before/after construction
    // leave the original journal intact for the consumer's cleanup/quarantine.
    for(int boundary=0;boundary<6;++boundary) {
        ConstructionJournal journal;int calls=0;
        auto operation=[&](int index){++calls;if(index==boundary)throw std::runtime_error("Lost acknowledgement");return true;};
        try {
            (void)construct(journal,[&](){return operation(0);},[&](){return operation(1);},
                [&](){return operation(2);},[&](){return operation(3);},[&](){return operation(4);},[&](){return operation(5);});
            return 4;
        } catch(const std::runtime_error&) {}
        if(!journal.attempted||journal.phase!=pending[boundary]||calls!=boundary+1)return 5;
        int forbidden_calls=0;auto forbidden=[&](){++forbidden_calls;return true;};
        if(construct(journal,forbidden,forbidden,forbidden,forbidden,forbidden,forbidden)!=ConstructionResult::AlreadyAttempted||forbidden_calls)return 6;
    }
    // An inconsistent persisted phase also refuses allocation, even if a
    // consumer accidentally presents an unmarked attempted flag.
    ConstructionJournal inconsistent;inconsistent.phase=ConstructionPhase::Retained;
    int forbidden_calls=0;auto forbidden=[&](){++forbidden_calls;return true;};
    if(construct(inconsistent,forbidden,forbidden,forbidden,forbidden,forbidden,forbidden)!=ConstructionResult::AlreadyAttempted||forbidden_calls)return 7;
    return 0;
}
