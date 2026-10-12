#pragma once
#include "media_owner_protocol.h"

// One media child of the currently owned panel. No story/native game widget
// may be registered: exact base class, same owned WidgetTree, retained lease.
class MediaOwner {
    uint64_t owner_=0,lease_=0;
    CallPacket plans_[2]{};
    MediaCleanupState cleanup_;
    static bool empty(const void* p,size_t n) {
        auto b=static_cast<const uint8_t*>(p);
        for(size_t i=0;i<n;++i) if(b[i]) return false;
        return true;
    }
public:
    bool active() const { return cleanup_.state!=0; }
    bool protects(uint64_t lease) const { return active() && lease==lease_; }
    uint32_t close(uint64_t base) {
        struct Ops {
            uint64_t base; CallPacket* plans;
            uint32_t invoke(uint32_t step) {
                auto c=plans[step];
                auto e=reflected_call(base,c);
                if(e==201 && c.outcome==CallNotDispatched) return 407;
                return !e && c.outcome==CallDispatchReturned ? 0 : 1403;
            }
        } ops{base,plans_};
        return cleanup_.close(ops);
    }
    template<class Pool>
    void command(uint64_t base,uint64_t session,Pool& leases,
                 const TargetMenuStorage& menu,MediaOwnerPacket& p) {
        if(p.version!=1 || !p.owner || p.error || p.state || p.operation<1 || p.operation>3) {
            p.error=1400; return;
        }
        p.state=cleanup_.state;
        if(p.operation!=1) {
            if(p.owner!=owner_ || p.lease || !empty(&p.close,sizeof(p.close)) ||
               !empty(&p.remove,sizeof(p.remove))) { p.error=1401; return; }
            if(p.operation==2) p.error=close(base);
            p.state=cleanup_.state; return;
        }
        if(active() || !menu.menu.active() || menu.session!=session || !p.lease ||
           !leases.owns_object(session,p.lease,p.close.target.address)) { p.error=1401; return; }
        const auto widget=call_identity(base,p.close.target);
        const auto cls=widget ? local_read<uint64_t>(widget+0x10) : 0;
        const auto tree=widget ? local_read<uint64_t>(widget+0x20) : 0;
        if(!widget || !call_is_class(base,cls) || !exact_name(base,cls+0x18,"CommonVideoPlayer") ||
           !exact_name(base,local_read<uint64_t>(cls+0x20)+0x18,"/Script/CommonUI") ||
           (local_read<uint32_t>(widget+8)&(0x10|0x40000000)) ||
           !tree || tree!=local_read<uint64_t>(menu.child.address+0x20) ||
           local_read<uint64_t>(tree+0x20)!=menu.widget.address) { p.error=1401; return; }
        const CallPacket* plans[]={&p.close,&p.remove};
        for(uint32_t i=0;i<2;++i) {
            const auto& c=*plans[i];
            auto fn=call_identity(base,c.function);
            auto owner=fn ? local_read<uint64_t>(fn+0x20) : 0;
            if(validate_call_packet(c) || c.parameter_size || c.field_count || c.object_count ||
               c.return_offset!=65535 || std::memcmp(&c.target,&p.close.target,sizeof(c.target)) ||
               !fn || !owner || !exact_name(base,fn+0x18,i ? "RemoveFromParent" : "Close") ||
               !exact_name(base,owner+0x18,i ? "Widget" : "CommonVideoPlayer") ||
               !exact_name(base,local_read<uint64_t>(owner+0x20)+0x18,i ? "/Script/UMG" : "/Script/CommonUI")) {
                p.error=1401; return;
            }
            auto copy=c;
            if(reflected_call(base,copy,nullptr,nullptr,nullptr,nullptr,true) || copy.outcome!=CallNotDispatched) {
                p.error=1402; return;
            }
        }
        plans_[0]=p.close; plans_[1]=p.remove; owner_=p.owner; lease_=p.lease;
        cleanup_.step=0; cleanup_.state=p.state=1;
    }
};
