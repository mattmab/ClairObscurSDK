#include "scoped_assignment.h"
#include <cassert>
#include <iostream>
struct Ops {
    uint64_t value=100;
    bool valid=true, available=true, fail_after_write=false;
    unsigned writes=0;
    bool context() { return available; }
    uint64_t validate(const ObjectAssignment&) { return valid ? 1 : 0; }
    uint64_t read(const ObjectAssignment&) { return value; }
    void assign(uint64_t,const ObjectAssignment& r) {
        ++writes; value=r.value.address;
        if(fail_after_write) available=false;
    }
};
int main() {
    ObjectAssignment p{};
    p.target=p.owner=p.constraint=p.expected={1,2,0x10000};
    p.value={2,3,0x20000}; p.offset=48; p.dimension=1; p.name[0]='X';
    {
        Ops ops; ops.value=p.expected.address; ScopedAssignment owner;
        assert(owner.open(ops,p)==ObjectAssignmentResult::Ok);
        assert(owner.active() && ops.value==p.value.address);
        ops.available=false;
        assert(owner.close(ops)==ObjectAssignmentResult::InvalidContext && owner.state()==1);
        ops.available=true;
        assert(owner.close(ops)==ObjectAssignmentResult::Ok && !owner.active());
        assert(ops.value==p.expected.address && ops.writes==2);
        assert(owner.close(ops)==ObjectAssignmentResult::Ok && ops.writes==2);
    }
    {
        Ops ops; ops.value=p.expected.address; ScopedAssignment owner;
        assert(owner.open(ops,p)==ObjectAssignmentResult::Ok);
        ops.value=0x30000;
        assert(owner.close(ops)==ObjectAssignmentResult::ChangedValue && owner.state()==2);
        assert(owner.close(ops)==ObjectAssignmentResult::UnknownOutcome && ops.writes==1);
    }
    {
        Ops ops; ops.value=p.expected.address; ops.fail_after_write=true; ScopedAssignment owner;
        assert(owner.open(ops,p)==ObjectAssignmentResult::UnknownOutcome && owner.state()==2);
        ops.available=true;
        assert(owner.close(ops)==ObjectAssignmentResult::UnknownOutcome && ops.writes==1);
    }
    {
        Ops ops; ops.value=p.expected.address; ops.valid=false; ScopedAssignment owner;
        assert(owner.open(ops,p)==ObjectAssignmentResult::StaleMetadata && !owner.active());
        assert(ops.writes==0);
    }
    std::cout << "scoped assignment ownership fixture passed\n";
}
