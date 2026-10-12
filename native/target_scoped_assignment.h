#pragma once
#include "scoped_assignment.h"
#include "scoped_assignment_protocol.h"
#include "target_object_assignment.h"

class TargetScopedAssignment {
    ScopedAssignment state_;
    uint64_t owner_=0,tokens_[3]{};
    static bool empty(const AssignmentPacket& p) {
        const auto* bytes=reinterpret_cast<const uint8_t*>(&p);
        for(size_t i=0;i<sizeof(p);++i) if(bytes[i]) return false;
        return true;
    }
public:
    bool active() const { return state_.active(); }
    bool protects(uint64_t token) const {
        return active() && (state_.state()==2 || token==tokens_[0] || token==tokens_[1] || token==tokens_[2]);
    }
    uint32_t close(uint64_t base) {
        TargetObjectAssignmentOps ops{base};
        auto result=state_.close(ops);
        if(result==ObjectAssignmentResult::Ok) return 0;
        return result==ObjectAssignmentResult::InvalidContext && state_.state()==1 ? 407 : 1483;
    }
    template<class Pool>
    void command(uint64_t base,uint64_t session,Pool& leases,bool menu_active,ScopedAssignmentPacket& p) {
        if(p.version!=1 || !p.owner || p.reserved || p.error || p.state || p.operation<1 || p.operation>3) {
            p.error=1480; return;
        }
        p.state=state_.state();
        if(p.operation!=1) {
            if(p.owner!=owner_ || !empty(p.assignment)) { p.error=1481; return; }
            if(p.operation==2) p.error=close(base);
            p.state=state_.state(); return;
        }
        const auto& w=p.assignment;
        const auto& a=w.assignment;
        if(active() || !menu_active || w.version!=1 || w.error || !valid_object_assignment(a) ||
           !a.expected.address || !a.value.address ||
           !leases.owns_object(session,w.target_token,a.target.address) ||
           !leases.owns_object(session,w.expected_token,a.expected.address) ||
           !leases.owns_object(session,w.value_token,a.value.address)) { p.error=1481; return; }
        owner_=p.owner;
        tokens_[0]=w.target_token; tokens_[1]=w.expected_token; tokens_[2]=w.value_token;
        TargetObjectAssignmentOps ops{base};
        auto result=state_.open(ops,a);
        p.state=state_.state();
        p.error=result==ObjectAssignmentResult::Ok ? 0 : 1482;
    }
};
