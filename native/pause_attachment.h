#pragma once
#include "pause_attachment_protocol.h"
#ifdef E33_RETIRED_WORLD_SESSION
#include "retired_world_target.h"
#endif

// One leased SDK-created button. Register durable detach before attaching it
// to a borrowed game panel. The target process remains the cleanup owner if
// Python disappears. Unknown dispatch is never replayed or released.
class PauseAttachment {
    uint64_t owner_=0, lease_=0;
    uint32_t state_=0;
    CallPacket remove_{};
    CallPacket restore_[2]{};
    uint64_t restore_lease_[2]{};
    uint32_t changed_[2]{};
#ifdef E33_RETIRED_WORLD_SESSION
    e33_retired_world::Anchor retired_anchor_;
    bool retired_cleanup_=false,removed_=false,capture_pending_=false;
    void* pool_=nullptr;uint64_t session_=0;
    uint32_t (*release_anchor_)(void*,uint64_t,e33_retired_world::Anchor&,uint64_t)=nullptr;
    template<class Pool>static uint32_t release_anchor(void*value,uint64_t base,e33_retired_world::Anchor&anchor,uint64_t session){
        e33_retired_world::TargetOps epoch{base};return anchor.release(epoch,*static_cast<Pool*>(value),session);
    }
#endif
public:
    uint64_t owner() const { return owner_; }
    bool active() const { return state_ != 0; }
    bool protects(uint64_t lease) const { return state_ && (lease_==lease || restore_lease_[0]==lease || restore_lease_[1]==lease
#ifdef E33_RETIRED_WORLD_SESSION
        || retired_anchor_.token()==lease
#endif
        ); }
    uint32_t restore(uint64_t base) {
#ifdef E33_RETIRED_WORLD_SESSION
        if(retired_cleanup_)return 1303;
        if(pool_){e33_retired_world::TargetOps epoch{base};
            const auto proof=epoch.current_binding(retired_anchor_.engine(),retired_anchor_.viewport(),retired_anchor_.world())?
                e33_retired_world::Result::SameWorld:retired_anchor_.prove(epoch);
            if(proof!=e33_retired_world::Result::SameWorld)return proof==e33_retired_world::Result::Pending?407:1303;
        }
#endif
        for(int i=1;i>=0;--i) {
            if(!changed_[i]) continue;
            if(changed_[i]!=1) return 1303;
            auto call=restore_[i]; changed_[i]=2;
            auto error=reflected_call(base,call);
            if(error==201 && call.outcome==CallNotDispatched) { changed_[i]=1; return 407; }
            if(error || call.outcome!=CallDispatchReturned) return 1303;
            changed_[i]=0;
        }
        return 0;
    }
    uint32_t close(uint64_t base,bool terminal) {
        if(terminal) { state_=0; owner_=lease_=0; restore_lease_[0]=restore_lease_[1]=0; changed_[0]=changed_[1]=0; return 0; }
        if(!state_) return 0;
#ifdef E33_RETIRED_WORLD_SESSION
        if(capture_pending_){
            if(!release_anchor_)return 1303;
            const auto error=release_anchor_(pool_,base,retired_anchor_,session_);
            if(error)return error;
            retired_anchor_.reset();capture_pending_=false;pool_=nullptr;release_anchor_=nullptr;session_=0;
            state_=0;owner_=lease_=0;return 0;
        }
#endif
        if(state_!=1) return 1303;
#ifdef E33_RETIRED_WORLD_SESSION
        if(pool_){e33_retired_world::TargetOps epoch{base};const auto proof=retired_anchor_.prove(epoch);
            if(proof==e33_retired_world::Result::Pending)return 407;
            if(proof==e33_retired_world::Result::Unknown)return 1303;
            if(proof==e33_retired_world::Result::Retired)retired_cleanup_=true;
        }
        if(retired_cleanup_){
            if(changed_[0]>1||changed_[1]>1)return 1303;
            changed_[0]=changed_[1]=0; // Proven retired world: no borrowed setters.
        }else
#endif
        {auto restored=restore(base); if(restored) return restored;}
#ifdef E33_RETIRED_WORLD_SESSION
        if(!removed_){
#endif
        auto call=remove_;
#ifdef E33_RETIRED_WORLD_SESSION
        const bool destroyed=retired_cleanup_ && (!call_identity(base,call.target) ||
            (local_read<uint32_t>(call.target.address+8)&0x40018030U));
        if(destroyed)removed_=true;
        if(!removed_){
#endif
        state_=2;
        auto error=reflected_call(base,call);
        if(error==201 && call.outcome==CallNotDispatched) { state_=1; return 407; }
        if(error || call.outcome!=CallDispatchReturned) { state_=2; return 1303; }
#ifdef E33_RETIRED_WORLD_SESSION
        state_=1;
        }
        removed_=true;
        }
        if(release_anchor_){auto error=release_anchor_(pool_,base,retired_anchor_,session_);if(error)return error;}
        retired_anchor_.reset();retired_cleanup_=removed_=false;pool_=nullptr;release_anchor_=nullptr;session_=0;
#endif
        state_=0; owner_=lease_=0; restore_lease_[0]=restore_lease_[1]=0;
        return 0;
    }
    template<class Pool>
    void command(uint64_t base,uint64_t session,Pool& leases,PauseAttachmentPacket& p) {
        if(p.version!=1 || p.operation<1 || p.operation>
#ifdef E33_RETIRED_WORLD_SESSION
            8
#else
            7
#endif
            || !p.owner || p.error || p.state) {
            p.error=1300; return;
        }
#ifdef E33_RETIRED_WORLD_SESSION
        if(p.operation==8){
            if(p.lease||!wire_empty(&p.remove,sizeof(p.remove))||!state_||p.owner!=owner_){p.error=1301;return;}
            if(capture_pending_){p.error=close(base,false);p.state=state_;return;}
            e33_retired_world::TargetOps epoch{base};const auto proof=retired_anchor_.prove(epoch);
            if(proof!=e33_retired_world::Result::Retired){p.error=proof==e33_retired_world::Result::Pending?407:1303;p.state=state_;return;}
            retired_cleanup_=true;p.error=close(base,false);p.state=state_;return;
        }
#endif
        if(p.operation>=3) {
#ifdef E33_RETIRED_WORLD_SESSION
            e33_retired_world::TargetOps epoch{base};
            const auto proof=epoch.current_binding(retired_anchor_.engine(),retired_anchor_.viewport(),retired_anchor_.world())?
                e33_retired_world::Result::SameWorld:retired_anchor_.prove(epoch);
            if(proof!=e33_retired_world::Result::SameWorld){p.error=proof==e33_retired_world::Result::Pending?407:1303;p.state=state_;return;}
#endif
            p.state=state_;
            if(state_!=1 || p.owner!=owner_) { p.error=1301; return; }
            if(p.operation==7) {
                if(p.lease || !wire_empty(&p.remove,sizeof(p.remove))) { p.error=1301; return; }
                p.error=restore(base); return;
            }
            unsigned i=(p.operation-3)%2;
            if(p.operation<=4) {
                auto& c=p.remove;
                if(restore_lease_[i] || !p.lease || !leases.owns_object(session,p.lease,c.target.address) ||
                   validate_call_packet(c) || c.field_count!=1 || c.object_count || c.return_offset!=65535 ||
                   c.fields[0].kind!=(i ? CallBool : CallFloat) || c.fields[0].dimension!=1) { p.error=1301; return; }
                auto fn=call_identity(base,c.function), obj=call_identity(base,c.target);
                if(!fn || !obj || !exact_name(base,fn+0x18,i ? "SetIsEnabled" : "SetRenderOpacity") ||
                   !exact_name(base,local_read<uint64_t>(fn+0x20)+0x18,"Widget") ||
                   !exact_name(base,local_read<uint64_t>(obj+0x10)+0x18,"Overlay")) { p.error=1301; return; }
                auto copy=c;
                if(reflected_call(base,copy,nullptr,nullptr,nullptr,nullptr,true)) { p.error=1302; return; }
                restore_[i]=c; restore_lease_[i]=p.lease; return;
            }
            if(p.lease || !restore_lease_[i] || changed_[i] || validate_call_packet(p.remove) ||
               std::memcmp(&p.remove,&restore_[i],offsetof(CallPacket,data)) ||
               !wire_empty(p.remove.data,sizeof(p.remove.data))) { p.error=1301; return; }
            auto call=p.remove; changed_[i]=2;
            auto error=reflected_call(base,call);
            if(error==201 && call.outcome==CallNotDispatched) { changed_[i]=0; p.error=407; return; }
            if(error || call.outcome!=CallDispatchReturned) { p.error=1303; return; }
            changed_[i]=1; return;
        }
        if(p.operation==2) {
            if(p.lease || !wire_empty(&p.remove,sizeof(p.remove)) || !state_ || p.owner!=owner_) {
                p.error=1301; return;
            }
            p.error=close(base,false); p.state=state_; return;
        }
        if(state_ || !p.lease || !leases.owns_object(session,p.lease,p.remove.target.address) ||
           validate_call_packet(p.remove) || p.remove.parameter_size || p.remove.field_count ||
           p.remove.object_count || p.remove.return_offset!=65535) { p.error=1301; return; }
        const auto fn=call_identity(base,p.remove.function), widget=call_identity(base,p.remove.target);
        if(!fn || !widget || !exact_name(base,fn+0x18,"RemoveFromParent") ||
           !exact_name(base,local_read<uint64_t>(fn+0x20)+0x18,"Widget") ||
           !exact_name(base,local_read<uint64_t>(widget+0x10)+0x18,"WBP_BaseButton_C") ||
           (local_read<uint32_t>(widget+8)&(0x10|0x40000000))) { p.error=1301; return; }
        auto call=p.remove;
        if(reflected_call(base,call,nullptr,nullptr,nullptr,nullptr,true) || call.outcome!=CallNotDispatched) {
            p.error=1302; return;
        }
#ifdef E33_RETIRED_WORLD_SESSION
        owner_=p.owner;lease_=p.lease;remove_=p.remove;state_=2;
        pool_=&leases;session_=session;release_anchor_=&release_anchor<Pool>;capture_pending_=true;
        e33_retired_world::TargetOps epoch{base};CallIdentity controller{};
        uint32_t owning_diagnostic=0;
        if(!epoch.owning_player(p.remove.target,controller,&owning_diagnostic)){p.error=owning_diagnostic?owning_diagnostic:2054;p.state=state_;return;}
        if(auto error=retired_anchor_.capture(epoch,leases,session,controller)){p.error=error;p.state=state_;return;}
        removed_=retired_cleanup_=capture_pending_=false;
#endif
        owner_=p.owner; lease_=p.lease; remove_=p.remove; state_=p.state=1;
    }
private:
    static bool wire_empty(const void* data,size_t size) {
        const auto* p=static_cast<const uint8_t*>(data);
        for(size_t i=0;i<size;++i) if(p[i]) return false;
        return true;
    }
};

// Bounded independent cleanup owners for sibling pause-menu entries.
class PauseAttachmentPool {
    PauseAttachment entries_[4];
public:
    bool protects(uint64_t lease) const {
        for(const auto& entry: entries_) if(entry.protects(lease)) return true;
        return false;
    }
    uint32_t close(uint64_t base,bool terminal) {
        uint32_t first=0;
        for(auto& entry: entries_) { auto error=entry.close(base,terminal); if(!first) first=error; }
        return first;
    }
    template<class Pool>
    void command(uint64_t base,uint64_t session,Pool& leases,PauseAttachmentPacket& p) {
        for(auto& entry: entries_) if(entry.active() && entry.owner()==p.owner) {
            entry.command(base,session,leases,p); return;
        }
        if(p.operation==1) for(auto& entry: entries_) if(!entry.active()) {
            entry.command(base,session,leases,p); return;
        }
        p.error=1301;
    }
};

