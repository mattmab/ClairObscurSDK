#pragma once
#include "cinematic_widget_journal.h"
#include "sequence_track_ownership.h"
#include "strong_lease_pool.h"
#ifdef E33_WIDGET_ANIMATION_SESSION
#include "cinematic_title_animation_owner.h"
#endif

// Internal native owner. Admission is called only by the exact profiled getter
// adapter, never by a generic Python pointer API. Wire/hook admission is separate.
class CinematicWidgetOwner {
#ifdef E33_WIDGET_ANIMATION_SESSION
    StrongLeasePool<kTitlePrivateLeaseCapacity> leases_;
    TitleAnimationOwner<StrongLeasePool<kTitlePrivateLeaseCapacity>> animations_;
#else
    StrongLeasePool<32> leases_;
#endif
    e33_cinematic::WidgetJournal<CallIdentity> journal_;
    uint64_t base_=0,session_=0;
    CallIdentity track_class_{},widget_class_{};
    CallPacket remove_{};
    struct Ops {
        CinematicWidgetOwner& self;
        bool valid(const CallIdentity& id) const { return call_identity(self.base_,id)!=0; }
        bool same(const CallIdentity& a,const CallIdentity& b) const { return !std::memcmp(&a,&b,sizeof(a)); }
        bool capacity(uint32_t n) const { return self.leases_.preflight(self.session_,n)==StrongLeaseResult::Ok; }
        bool retain(CallIdentity& id,uint64_t& token) {
            TargetStrongReferenceOps ops{self.base_,id};
            if(self.leases_.acquire(ops,self.session_,id.address,token)!=StrongLeaseResult::Ok) return false;
            id=call_capture(self.base_,id.address); return id.address!=0;
        }
        e33_cinematic::WidgetStep detach(const CallIdentity& id) {
#ifdef E33_WIDGET_ANIMATION_SESSION
            const auto animation=self.animations_.close_widget(id);
            if(animation!=e33_cinematic::WidgetStep::ok) return animation;
#endif
            auto call=self.remove_;call.target=id;
            const auto error=reflected_call(self.base_,call);
            if(error==201 && call.outcome==CallNotDispatched) return e33_cinematic::WidgetStep::deferred;
            return !error && call.outcome==CallDispatchReturned ? e33_cinematic::WidgetStep::ok : e33_cinematic::WidgetStep::uncertain;
        }
        e33_cinematic::WidgetStep release_all() {
#ifdef E33_WIDGET_ANIMATION_SESSION
            // The journal skips destroyed widget identities. That must not
            // silently release a separately retained player still draining.
            if(!self.animations_.safe_to_release()) return e33_cinematic::WidgetStep::uncertain;
#endif
            TargetStrongReferenceOps ops{self.base_,{}};
            const auto result=self.leases_.close(ops,self.session_);
            if(result==StrongLeaseResult::Deferred) return e33_cinematic::WidgetStep::deferred;
            return result==StrongLeaseResult::Ok ? e33_cinematic::WidgetStep::ok : e33_cinematic::WidgetStep::uncertain;
        }
    };
public:
    bool active() const { return journal_.active_owner(); }
    size_t private_active() const { return leases_.active(); }
    size_t private_peak() const { return leases_.peak(); }
    bool matches(const CallIdentity& player,const CallIdentity& track) {
        Ops ops{*this};
        if(!call_identity(base_,player) || !call_identity(base_,track) ||
           !call_identity(base_,track_class_) || local_read<uint64_t>(track.address+0x10)!=track_class_.address) return false;
        if(journal_.owns_track(ops,track)) return true;
        e33_cinematic::TrackRootMatch match{};
        auto read=[](uint64_t address,void* out,size_t size) {
            std::memcpy(out,reinterpret_cast<const void*>(address),size);return true;};
        return e33_cinematic::match_root_track(read,player.address,track.address,match);
    }
    // Caller additionally validates exact game profile, private component and
    // retains the class/function identities for this owner's complete lifetime.
    bool begin(uint64_t base,uint64_t session,const CallIdentity& track_class,
               const CallIdentity& widget_class,const CallPacket& remove) {
        if(active() || !call_identity(base,track_class) || !call_identity(base,widget_class)) return false;
        if(!call_is_class(base,track_class.address) || !call_is_class(base,widget_class.address) ||
           !exact_name(base,track_class.address+0x18,"BP_WidgetSequencerTrackInstance_C") ||
           !exact_name(base,local_read<uint64_t>(track_class.address+0x20)+0x18,
               "/Game/Gameplay/UI/Sequencer/BP_WidgetSequencerTrackInstance") ||
           !exact_name(base,widget_class.address+0x18,"UserWidget") ||
           !exact_name(base,local_read<uint64_t>(widget_class.address+0x20)+0x18,"/Script/UMG")) return false;
        const auto field=music_field(base,track_class.address,"SpawnedUserWidget",88,8,0x6e11d38,0x8001000090205ULL);
        if(!field || local_read<uint64_t>(field+0x70)!=widget_class.address) return false;
        auto test=remove;
        const auto fn=call_identity(base,remove.function);
        const auto owner=fn ? local_read<uint64_t>(fn+0x20) : 0;
        if(!fn || !owner || remove.parameter_size || remove.allocation_extent || remove.field_count ||
           remove.object_count || remove.return_offset!=65535 || validate_call_packet(remove) ||
           !exact_name(base,fn+0x18,"RemoveFromParent") || !exact_name(base,owner+0x18,"Widget") ||
           !exact_name(base,local_read<uint64_t>(owner+0x20)+0x18,"/Script/UMG") ||
           reflected_call(base,test,nullptr,nullptr,nullptr,nullptr,true)) return false;
#ifdef E33_WIDGET_ANIMATION_SESSION
        if(!animations_.prepare(base,widget_class)) return false;
#endif
        if(leases_.begin(session)!=StrongLeaseResult::Ok) return false;
#ifdef E33_WIDGET_ANIMATION_SESSION
        animations_.begin(base,session,leases_);
#endif
        base_=base;session_=session;track_class_=track_class;widget_class_=widget_class;remove_=remove;
        return journal_.begin();
    }
    bool admit(const CallIdentity& player,const CallIdentity& track) {
        TargetObjectAssignmentOps context{base_};Ops ops{*this};
        if(!context.context() || !call_identity(base_,player) || !call_identity(base_,track) ||
           !call_identity(base_,track_class_) || !call_identity(base_,widget_class_) ||
           local_read<uint64_t>(track.address+0x10)!=track_class_.address) return false;
        if(!journal_.owns_track(ops,track)) {
            e33_cinematic::TrackRootMatch match{};
            auto read=[](uint64_t address,void* output,size_t size) {
                std::memcpy(output,reinterpret_cast<const void*>(address),size);return true;};
            // Containing native hook must provide an SEH boundary. No result
            // substitution is allowed if this read or later retention faults.
            if(!e33_cinematic::match_root_track(read,player.address,track.address,match)) return false;
        }
        const auto widget=local_read<uint64_t>(track.address+88);
        if(!widget) return journal_.owns_track(ops,track);
        auto id=call_capture(base_,widget);
        if(!id.address || !call_derives(base_,local_read<uint64_t>(widget+0x10),widget_class_.address)) return false;
#ifdef E33_WIDGET_ANIMATION_SESSION
        if(!journal_.admit(ops,track,id)) return false;
        id=call_capture(base_,widget);
        return animations_.register_widget(id);
#else
        return journal_.admit(ops,track,id);
#endif
    }
    e33_cinematic::WidgetStep close() {
        TargetObjectAssignmentOps context{base_};
        if(!context.context()) return e33_cinematic::WidgetStep::deferred;
        Ops ops{*this};return journal_.close(ops);
    }
};
