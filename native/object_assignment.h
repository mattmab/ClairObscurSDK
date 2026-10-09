#pragma once
#include "invocation_protocol.h"

// Experimental v10 primitive, not yet validated live.
// Callers must retain their objects, own the game thread, and contain native
// faults outside this frame. A dispatched failure must never be retried.
#pragma pack(push, 1)
struct ObjectAssignment {
    CallIdentity target{}, owner{}, constraint{}, expected{}, value{};
    uint64_t flags=0;
    uint32_t offset=0, dimension=0, element=0;
    char name[96]{};
    uint32_t outcome=CallNotDispatched;
};
#pragma pack(pop)
static_assert(sizeof(ObjectAssignment)==200);
enum class ObjectAssignmentResult {
    Ok, InvalidRequest, InvalidContext, StaleMetadata, ChangedValue, UnknownOutcome
};
inline bool assignment_identity(const CallIdentity& id,bool nullable) {
    return (nullable && id.index==-1 && id.serial==0 && !id.address) ||
        (id.index>=0 && id.serial>=0 && id.address>=0x10000 && id.address<0x7fffffffffff);
}
inline bool valid_object_assignment(const ObjectAssignment& r) {
    if(r.outcome!=CallNotDispatched || !assignment_identity(r.target,false) ||
       !assignment_identity(r.owner,false) || !assignment_identity(r.constraint,false) ||
       !assignment_identity(r.expected,true) || !assignment_identity(r.value,true) ||
       !r.name[0] || r.name[95] || !r.dimension || r.dimension>64 ||
       r.element>=r.dimension || r.offset<40 || uint64_t(r.offset)+uint64_t(r.dimension)*8>16777216)
        return false;
    for(unsigned i=0;i<96 && r.name[i];++i)
        if(static_cast<unsigned char>(r.name[i])>=128) return false;
    // Target setter silently refuses null when this observed flag is set.
    if(!r.value.address && (r.flags&0x1000)) return false;
    return true;
}
template<class Ops>
ObjectAssignmentResult assign_object_property(Ops& ops,ObjectAssignment& request) {
    if(!valid_object_assignment(request)) return ObjectAssignmentResult::InvalidRequest;
    if(!ops.context()) return ObjectAssignmentResult::InvalidContext;
    uint64_t property=ops.validate(request);
    if(!property) return ObjectAssignmentResult::StaleMetadata;
    if(ops.read(request)!=request.expected.address) return ObjectAssignmentResult::ChangedValue;
    if(!ops.context()) return ObjectAssignmentResult::InvalidContext;
    // Set before calling: an SEH fault or callback may occur after the write.
    request.outcome=CallOutcomeUnknown;
    ops.assign(property,request);
    if(!ops.context() || ops.validate(request)!=property || ops.read(request)!=request.value.address)
        return ObjectAssignmentResult::UnknownOutcome;
    request.outcome=CallDispatchReturned;
    return ObjectAssignmentResult::Ok;
}
