#include "object_assignment.h"
#include <cassert>
#include <stdexcept>
#include <cstdio>

struct FakeOps {
    bool available=true, metadata=true, lose_context=false, throw_after_write=false;
    uint64_t stored=0, property=0x90000;
    unsigned writes=0;
    bool context() const { return available; }
    uint64_t validate(const ObjectAssignment&) const { return metadata ? property : 0; }
    uint64_t read(const ObjectAssignment&) const { return stored; }
    void assign(uint64_t p,const ObjectAssignment& r) {
        assert(p==property);
        ++writes; stored=r.value.address;
        if(lose_context) available=false;
        if(throw_after_write) throw std::runtime_error("fault after native write");
    }
};
ObjectAssignment specimen() {
    ObjectAssignment r;
    r.target={1,20,0x10000}; r.owner={2,21,0x20000}; r.constraint={3,22,0x30000};
    r.expected={-1,0,0}; r.value={4,23,0x40000};
    r.offset=48; r.dimension=1;
    std::memcpy(r.name,"RootWidget",sizeof("RootWidget"));
    return r;
}
int main() {
    {
        FakeOps ops; auto r=specimen();
        assert(assign_object_property(ops,r)==ObjectAssignmentResult::Ok);
        assert(ops.stored==r.value.address && ops.writes==1 && r.outcome==CallDispatchReturned);
        // The already-dispatched request cannot accidentally be reused.
        assert(assign_object_property(ops,r)==ObjectAssignmentResult::InvalidRequest);
        assert(ops.writes==1);
    }
    {
        FakeOps ops; ops.stored=0x50000; auto r=specimen();
        assert(assign_object_property(ops,r)==ObjectAssignmentResult::ChangedValue);
        assert(ops.writes==0 && r.outcome==CallNotDispatched);
    }
    {
        FakeOps ops; ops.lose_context=true; auto r=specimen();
        assert(assign_object_property(ops,r)==ObjectAssignmentResult::UnknownOutcome);
        assert(ops.writes==1 && r.outcome==CallOutcomeUnknown);
    }
    {
        FakeOps ops; ops.throw_after_write=true; auto r=specimen();
        try { assign_object_property(ops,r); assert(false); }
        catch(const std::runtime_error&) {}
        assert(ops.stored==r.value.address && r.outcome==CallOutcomeUnknown);
        assert(assign_object_property(ops,r)==ObjectAssignmentResult::InvalidRequest);
        assert(ops.writes==1);
    }
    {
        FakeOps ops; ops.metadata=false; auto r=specimen();
        assert(assign_object_property(ops,r)==ObjectAssignmentResult::StaleMetadata);
        assert(!ops.writes);
        ops.metadata=true; ops.available=false;
        assert(assign_object_property(ops,r)==ObjectAssignmentResult::InvalidContext);
        assert(!ops.writes);
    }
    {
        FakeOps ops; auto r=specimen(); r.value={-1,0,0}; r.flags=0x1000;
        assert(assign_object_property(ops,r)==ObjectAssignmentResult::InvalidRequest);
        r.flags=0; r.element=1;
        assert(assign_object_property(ops,r)==ObjectAssignmentResult::InvalidRequest);
        r.element=0; r.expected={0,0,0};
        assert(assign_object_property(ops,r)==ObjectAssignmentResult::InvalidRequest);
        assert(!ops.writes);
    }
    std::puts("Object assignment: stale preconditions, context loss, post-write fault and no-retry checks passed.");
}
