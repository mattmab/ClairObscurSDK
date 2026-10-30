#pragma once
#include "sequencer_array_schema.h"
#include "target_pod_schema.h"
#include "target_strong_reference.h"
#include "stable_identity.h"

template<class Pool> struct TargetSequencerArrayOps:TargetPodSchemaOps {
    using TargetPodSchemaOps::capture;
    uint64_t session;Pool& pool;const e33_sequencer_array::Packet& packet;
    bool registered(uint64_t p) const {return p && identity(capture(p));}
    bool is_class(uint64_t p) const {return call_is_class(base,p);}
    bool derives(uint64_t c,uint64_t parent) const {return call_derives(base,c,parent);}
    bool validate() {
        return pool.owns_object(session,packet.subject_token,packet.subject.address) && sequencer_array_schema(*this,packet);
    }
    bool preflight(uint32_t count) const {return pool.preflight(session,count)==StrongLeaseResult::Ok;}
    void dispatch(void* arguments) const {
        const auto entry=read<uint64_t>(read<uint64_t>(packet.target.address)+0x268);
        reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(entry)(reinterpret_cast<void*>(packet.target.address),
            reinterpret_cast<void*>(packet.function.address),arguments);
    }
    bool read_pointer(uint64_t at,uint64_t& out) const {out=read<uint64_t>(at);return true;}
    bool capture(uint64_t object,CallIdentity& out) const {
        out=call_capture(base,object);if(!identity(out) || (read<uint32_t>(object+8)&0x40018030))return false;
        auto cls=read<uint64_t>(object+16);SequenceOriginSchema<const TargetSequencerArrayOps> fields(*this);
        for(unsigned i=0;cls && i<128;++i,cls=read<uint64_t>(cls+0x40))
            if(is_class(cls) && fields.named(cls,packet.mode==1 ? "MovieSceneScriptingChannel" : "MovieSceneScriptingKey","/Script/SequencerScripting"))return true;
        return false;
    }
    bool retain(CallIdentity& id,uint64_t& token) {
        TargetStrongReferenceOps ops{base,id};
        return pool.acquire(ops,session,id.address,token)==StrongLeaseResult::Ok && stabilize_retained_identity(ops,id);
    }
    void free_array(uint64_t address) const {
        reinterpret_cast<void(__fastcall*)(void*)>(base+0x107c7d0)(reinterpret_cast<void*>(address));
    }
};

template<class Pool> void sequencer_array_command(uint64_t base,uint64_t session,Pool& pool,
        e33_sequencer_array::Packet& p,e33_sequencer_array::Frame& frame) {
    using namespace e33_sequencer_array;
    if(!request(p) || !frame.available()){p.error=3741;return;}
    TargetSequencerArrayOps<Pool> ops{{base},session,pool,p};
    const auto result=frame.query(ops,p);
    if(result==Result::rejected){p.error=3741;return;}
    if(result==Result::unknown){p.error=3743;p.state=p.outcome=2;return;}
    p.state=p.outcome=1;p.total=frame.total();p.count=frame.count();
    if(result==Result::range)p.error=3744;
    std::memcpy(p.outputs,frame.outputs(),p.count*sizeof(Output));
    frame.reset();
}
