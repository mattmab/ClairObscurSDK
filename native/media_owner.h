#pragma once
#include "media_owner_protocol.h"
#if defined(E33_RETIRED_WORLD_SESSION) && E33_RUNTIME_CINEMATIC_VERSION>=216
#define E33_MEDIA_RETIREMENT_SESSION 1
#include "sequence_retirement.h"
#include "retired_world_target.h"
#endif

// One media child of the currently owned panel. No story/native game widget
// may be registered: exact base class, same owned WidgetTree, retained lease.
class MediaOwner {
    uint64_t owner_=0,lease_=0;
    CallPacket plans_[2]{};
    MediaCleanupState cleanup_;
#ifdef E33_MEDIA_RETIREMENT_SESSION
    e33_retired_world::Snapshot epoch_{};
    bool retired_=false,retiring_=false;
    uint64_t epoch_menu_owner_=0;
#endif
    static bool empty(const void* p,size_t n) {
        auto b=static_cast<const uint8_t*>(p);
        for(size_t i=0;i<n;++i) if(b[i]) return false;
        return true;
    }
public:
    uint64_t captured_menu_owner()const{
#ifdef E33_MEDIA_RETIREMENT_SESSION
        return epoch_menu_owner_;
#else
        return 0;
#endif
    }
#ifdef E33_MEDIA_RETIREMENT_SESSION
    template<class Pool> uint32_t retirement_authority(uint64_t base,uint64_t session,Pool& leases,
            const MediaOwnerPacket& p,e33_retired_world::Snapshot& out) {
        out={};
        if(p.version!=1 || p.operation!=4 || !p.owner || p.owner!=owner_ || p.lease || p.error || p.state ||
           !empty(&p.close,sizeof(p.close)+sizeof(p.remove)) || cleanup_.state==2)return 1403;
        e33_retired_world::TargetOps proof{base};e33_retired_world::Snapshot a{},b{};
        if(!proof.observe(a) || !proof.observe(b))return 407;
        if(!e33_sequence_retirement::different_world(epoch_,a,b))return 1404;
        if(!leases.owns_retirement_storage(session,lease_,plans_[0].target.address))return 1403;
        retiring_=true;out=epoch_;return 0;
    }
#endif
    bool active() const { return cleanup_.state!=0; }
    uint32_t current_state()const{return cleanup_.state;}
    bool protects(uint64_t lease) const { return active() && lease==lease_; }
    uint32_t close(uint64_t base) {
#ifdef E33_MEDIA_RETIREMENT_SESSION
        if(retired_)return cleanup_.state ? 1403 : 0;
        if(retiring_)return cleanup_.state ? 407 : 0;
        if(cleanup_.state) {
            e33_retired_world::TargetOps proof{base};
            if(!proof.current_binding(epoch_.engine,epoch_.viewport,epoch_.world))return 407;
        }
#endif
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
        if(p.version!=1 || !p.owner || p.error || p.state || p.operation<1 || p.operation>
#ifdef E33_MEDIA_RETIREMENT_SESSION
           4
#else
           3
#endif
           ) {
            p.error=1400; return;
        }
        p.state=cleanup_.state;
        if(p.operation!=1) {
            if(p.owner!=owner_ || p.lease || !empty(&p.close,sizeof(p.close)) ||
               !empty(&p.remove,sizeof(p.remove))) { p.error=1401; return; }
#ifdef E33_MEDIA_RETIREMENT_SESSION
            if(p.operation==4) {
                if(!cleanup_.state)return;
                if(cleanup_.state==2){p.error=1403;return;}
                e33_retired_world::TargetOps proof{base};e33_retired_world::Snapshot a{},b{};
                if(!proof.observe(a) || !proof.observe(b)){p.error=407;return;}
                if(!e33_sequence_retirement::different_world(epoch_,a,b)){p.error=1404;return;}
                const bool owned=leases.owns_retirement_storage(session,lease_,plans_[0].target.address);
                // No CommonVideoPlayer.Close or old widget RemoveFromParent.
                // The caller retires its parent menu/input owner separately.
                p.error=cleanup_.retire(true,owned);p.state=cleanup_.state;
                if(!p.error)retired_=true;return;
            }
#endif
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
#ifdef E33_MEDIA_RETIREMENT_SESSION
        e33_retired_world::TargetOps proof{base};e33_retired_world::Snapshot a{},b{};
        if(!proof.observe(a) || a.world.serial<=0 || !proof.controller_world(menu.player,a.world) || !proof.observe(b) ||
           !e33_retired_world::same(a.engine,b.engine) || !e33_retired_world::same(a.viewport,b.viewport) ||
           !e33_retired_world::same(a.world,b.world)){p.error=1404;return;}
        epoch_=a;retired_=retiring_=false;epoch_menu_owner_=menu.owner;
#endif
        plans_[0]=p.close; plans_[1]=p.remove; owner_=p.owner; lease_=p.lease;
        cleanup_.step=0; cleanup_.state=p.state=1;
    }
};
