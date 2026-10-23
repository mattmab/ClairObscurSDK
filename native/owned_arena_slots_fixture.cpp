#include "owned_arena_slots.h"
#include "owned_actor_construction.h"
#include <cassert>
#include <stdexcept>
int main(){
    using namespace e33_owned_arena;
    Slots slots;
    assert(slots.reserve(0)==-1&&slots.find(0)==-1);
    const int a=slots.reserve(101),b=slots.reserve(202);
    assert(a==0&&b==1&&slots.find(101)==a&&slots.find(202)==b);
    assert(slots.find(303)==-1&&slots.reserve(303)==-1);
    assert(slots.reserve(101)==-1&&slots.reserve(202)==-1);
    // A failure before Owner records its own token still consumes capacity.
    assert(!slots.retired(a,3602,false)&&slots.find(101)==a);
    assert(!slots.retired(b,407,true)&&slots.find(202)==b);
    assert(!slots.retired(a,0,true)&&slots.reserve(303)==-1);
    assert(!slots.retired(2,0,false));
    assert(slots.retired(b,0,false)&&slots.find(202)==-1);
    assert(slots.find(101)==a&&slots.reserved(a));
    assert(slots.reserve(303)==b&&slots.find(303)==b);
    assert(slots.retired(a,0,false)&&slots.find(303)==b);
    assert(slots.retired(a,0,false)); // duplicate acknowledged retirement

    using namespace e33_owned_actor;
    ConstructionJournal journal;
    assert(!allocation_unresolved(journal,false));
    auto yes=[](){return true;};
    volatile bool lose_ack=true;
    try{
        construct(journal,[&](){if(lose_ack)throw std::runtime_error("allocation ack lost");return true;},yes,yes,yes,yes,yes);
        assert(false);
    }catch(const std::runtime_error&){}
    assert(allocation_unresolved(journal,false));
    assert(allocation_unresolved(journal,true)); // a prior stale identity cannot prove this allocation
    for(auto phase:{ConstructionPhase::Allocated,ConstructionPhase::IdentityPending}){
        journal.phase=phase;assert(allocation_unresolved(journal,false));
    }
    assert(!allocation_unresolved(journal,true)); // identify callback captured the current actor
    // After destruction, actor identity may be empty while lease release needs
    // retry. That is not an unobserved allocation and must not be quarantined.
    journal.phase=ConstructionPhase::Complete;assert(!allocation_unresolved(journal,false));
    return 0;
}
