#pragma once
#include "target_portable_binding.h"
#include "bound_object_frame.h"
#include "target_strong_reference.h"

// Research-only bridge from a native owner's retained inputs to the existing
// durable GetPortableBindingID frame. Inputs must come from the owner, never a
// wire packet; the enclosing authority must independently prove owner, unique
// source occurrence, and GUID membership before and after calling this.
namespace e33_authored_binding {
struct PortableInputs {
    CallIdentity target{},function{},root{},source{};
    uint64_t target_token=0,function_token=0,root_token=0,source_token=0;
};
class PortableResolver {
    e33_portable_binding::Frame frame_;
    bool tainted_=false;
public:
    bool uncertain()const{return tainted_ || frame_.quarantined();}
    template<class Ops>
    e33_camera_binding::QueryResult resolve(Ops& ops,const PortableInputs& in,
            const uint32_t (&guid)[4],e33_camera_binding::BindingValue& out) {
        using e33_camera_binding::QueryResult;
        out={};
        if(uncertain() || !frame_.available() || !ops.context() || !ops.owns(in))return QueryResult::rejected;
        e33_portable_binding::Packet p{};
        p.version=3;p.operation=e33_portable_binding::operation;p.request=1;
        p.target=in.target;p.function=in.function;p.root=p.destination=in.root;p.source=in.source;
        p.tokens[0]=in.target_token;p.tokens[1]=in.function_token;
        p.tokens[2]=p.tokens[3]=in.root_token;p.tokens[4]=in.source_token;
        std::memcpy(p.guid,guid,sizeof(p.guid));
        // The caller's adapter binds the same packet to the real schema and
        // lease validator; the frame does not persist this reference.
        const auto result=ops.query(frame_,p);
        if(result==e33_portable_binding::Result::Rejected)return QueryResult::rejected;
        if(result==e33_portable_binding::Result::Unknown)return QueryResult::unknown;
        if(result==e33_portable_binding::Result::Unavailable) {
            frame_.reset();return QueryResult::rejected;
        }
        const auto bytes=frame_.result();
        if(!bytes || !ops.context() || !ops.owns(in)) {tainted_=true;return QueryResult::unknown;}
        std::memcpy(&out,bytes,sizeof(out));
        frame_.reset();return QueryResult::ok;
    }
};

// Concrete adapter usable by a native owner whose private leases include all
// four inputs. It does not assert source reachability or GUID membership.
template<class Pool> struct PortableResolverOps {
    uint64_t base,session;Pool& leases;
    bool context()const {TargetStrongReferenceOps guard{base,{}};return guard.can_assign();}
    bool owns(const PortableInputs& in)const {
        const CallIdentity ids[]{in.target,in.function,in.root,in.source};
        const uint64_t tokens[]{in.target_token,in.function_token,in.root_token,in.source_token};
        for(unsigned i=0;i<4;++i)
            if(!call_identity(base,ids[i]) || !leases.owns_object(session,tokens[i],ids[i].address))return false;
        return context();
    }
    e33_portable_binding::Result query(e33_portable_binding::Frame& frame,const e33_portable_binding::Packet& p) {
        TargetPortableBindingOps<Pool> ops{{base},session,leases,p};
        return frame.query(ops,p);
    }
};
}
