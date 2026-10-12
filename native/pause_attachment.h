#pragma once
#include "pause_attachment_protocol.h"

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
public:
    uint64_t owner() const { return owner_; }
    bool active() const { return state_ != 0; }
    bool protects(uint64_t lease) const { return state_ && (lease_==lease || restore_lease_[0]==lease || restore_lease_[1]==lease); }
    uint32_t restore(uint64_t base) {
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
        if(state_!=1) return 1303;
        auto restored=restore(base); if(restored) return restored;
        auto call=remove_;
        state_=2;
        auto error=reflected_call(base,call);
        if(error==201 && call.outcome==CallNotDispatched) { state_=1; return 407; }
        if(error || call.outcome!=CallDispatchReturned) { state_=2; return 1303; }
        state_=0; owner_=lease_=0; restore_lease_[0]=restore_lease_[1]=0;
        return 0;
    }
    template<class Pool>
    void command(uint64_t base,uint64_t session,Pool& leases,PauseAttachmentPacket& p) {
        if(p.version!=1 || p.operation<1 || p.operation>7 || !p.owner || p.error || p.state) {
            p.error=1300; return;
        }
        if(p.operation>=3) {
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

