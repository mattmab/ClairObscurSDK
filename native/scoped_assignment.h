#pragma once
#include "object_assignment.h"

// Durable compare-and-restore ownership. A failed/unknown dispatched write is
// quarantined; only a positively un-dispatched context failure may be retried.
// Ops and leases stay outside this state machine so fixtures use the same code.
class ScopedAssignment {
    ObjectAssignment restore_{};
    uint32_t state_=0;
public:
    uint32_t state() const { return state_; }
    bool active() const { return state_!=0; }
    const ObjectAssignment& restore() const { return restore_; }
    template<class Ops>
    ObjectAssignmentResult open(Ops& ops,const ObjectAssignment& request) {
        if(active() || !valid_object_assignment(request) ||
           request.expected.address==request.value.address)
            return ObjectAssignmentResult::InvalidRequest;
        // Publish restoration data before the first possible engine mutation.
        restore_=request;
        restore_.expected=request.value;
        restore_.value=request.expected;
        auto copy=request;
        state_=2;
        auto result=assign_object_property(ops,copy);
        if(result==ObjectAssignmentResult::Ok) state_=1;
        else if(copy.outcome==CallNotDispatched) state_=0;
        return result;
    }
    template<class Ops>
    ObjectAssignmentResult close(Ops& ops) {
        if(!active()) return ObjectAssignmentResult::Ok;
        if(state_==2) return ObjectAssignmentResult::UnknownOutcome;
        auto copy=restore_;
        state_=2;
        auto result=assign_object_property(ops,copy);
        if(result==ObjectAssignmentResult::Ok) state_=0;
        else if(result==ObjectAssignmentResult::InvalidContext && copy.outcome==CallNotDispatched)
            state_=1;
        // ChangedValue is deliberately not overwritten, even on disconnect.
        return result;
    }
};
