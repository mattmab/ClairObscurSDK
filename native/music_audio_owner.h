#pragma once
#include "retired_collector_release.h"
#include "music_audio_owner_protocol.h"
#include "music_audio_profile.h"
#include "strong_lease_pool.h"
#include "owned_sound_factory.h"
#include "audio_cleanup_diagnostics.h"
#include "stable_identity.h"
#include "audio_destroy_completion.h"
#ifdef E33_ORIGINAL_AUDIO_PAUSE_SESSION
#include "original_audio_pause.h"
#endif
#ifdef E33_CINEMATIC_EPOCH_RETIRE_SESSION
#include "cinematic_current_music.h"
#endif

// Game adapter: owns components found only in an initially-empty private music
// system. Strong container references remain retained until all calls return.
// This does NOT cover GameplayStatics.PlaySound2D (no component is returned).
class MusicAudioOwner {
    uint32_t state_=0,index_=0,step_=0;
    uint64_t owner_=0,tokens_[2]{};
    uint64_t component_tokens_[kOwnedAudioCleanupCapacity]{};
    // Cleanup must not compete with menu/mod leases. Reserve a bounded private
    // pool before playback admission; its tokens never cross the wire.
    StrongLeasePool<kOwnedAudioCleanupCapacity> component_leases_;
    CallIdentity original_{},isolated_{},audio_{};
    MusicAudioReferences originals_{};
    MusicAudioReferenceSet<kOwnedAudioCleanupCapacity> cleanup_{};
    CallIdentity explicit_components_[kExplicitSoundCapacity]{};
    CallIdentity explicit_sounds_[kExplicitSoundCapacity]{};
    uint64_t explicit_tokens_[kExplicitSoundCapacity]{};
    static_assert(sizeof(explicit_components_)+sizeof(explicit_sounds_)+sizeof(explicit_tokens_)==kExplicitSoundCapacity*40);
    static_assert(StrongLeasePool<kOwnedAudioCleanupCapacity>::maximum==kOwnedAudioCleanupCapacity);
    uint32_t explicit_count_=0;
    CallPacket stop_{},destroy_{};
#ifdef E33_CINEMATIC_EPOCH_RETIRE_SESSION
    e33_retired_world::Snapshot epoch_{};
    CallIdentity gi_{};
    bool retiring_=false;
    uint64_t menu_owner_=0;
#endif
#ifdef E33_AUDIO_CLEANUP_DIAGNOSTICS_SESSION
    AudioCleanupDiagnostics diagnostics_;
#endif
    void diagnostic_phase(AudioCleanupPhase phase,uint32_t index=0,uint32_t step=0) {
#ifdef E33_AUDIO_CLEANUP_DIAGNOSTICS_SESSION
        diagnostics_.phase(phase,index,step);
#else
        (void)phase;(void)index;(void)step;
#endif
    }
    void diagnostic_failure(uint32_t reason=1,uint32_t error=0,uint32_t outcome=0) {
#ifdef E33_AUDIO_CLEANUP_DIAGNOSTICS_SESSION
        diagnostics_.returned(error,outcome);diagnostics_.failure(reason);
#else
        (void)reason;(void)error;(void)outcome;
#endif
    }
    bool completed_destroy(uint64_t base,uint64_t session,const CallIdentity& identity,uint64_t token,
                           uint32_t error,uint32_t outcome,uint32_t detail) const {
        struct Ops {
            uint64_t base;const StrongLeasePool<kOwnedAudioCleanupCapacity>& leases;CallIdentity audio;
            bool context() const { return TargetObjectAssignmentOps{base}.context(); }
            bool owns(uint64_t session,uint64_t token,uint64_t address) const {
                return leases.owns_object(session,token,address);
            }
            bool matches(const CallIdentity& id) const { return call_identity(base,id)==id.address; }
            bool exact_class(const CallIdentity& id) const {
                return call_identity(base,audio) && local_read<uint64_t>(id.address+0x10)==audio.address;
            }
            AudioDestroyMarkers markers(const CallIdentity& id) const {
                // Called only after exact index/serial/address and holder checks.
                const auto chunks=local_read<uint64_t>(base+0x9361b70);
                const auto slot=local_read<uint64_t>(chunks+uint64_t(id.index>>16)*8)+uint64_t(id.index&65535)*24;
                return {local_read<uint32_t>(id.address+8),local_read<uint32_t>(slot+8),
                    local_read<uint8_t>(id.address+0x8b),local_read<uint8_t>(id.address+0x8a)};
            }
        } ops{base,component_leases_,audio_};
        return completed_audio_destruction(ops,state_,step_,error,outcome,detail,session,token,identity);
    }
    void diagnostic_counts(uint32_t now,uint32_t current) {
#ifdef E33_AUDIO_CLEANUP_DIAGNOSTICS_SESSION
        diagnostics_.counts(originals_.count,now,current);
#else
        (void)now;(void)current;
#endif
    }
#ifdef E33_ORIGINAL_AUDIO_PAUSE_SESSION
    OriginalAudioPause original_pause_;
#endif
public:
#ifdef E33_AUDIO_CLEANUP_DIAGNOSTICS_SESSION
    AudioCleanupSnapshot cleanup_diagnostics() const { return diagnostics_.snapshot(state_); }
#endif
    bool active() const { return state_!=0; }
    bool owns_component(const CallIdentity& id,const CallIdentity& sound) const {
        if(state_!=1) return false;
        for(unsigned i=0;i<explicit_count_;++i)
            if(!std::memcmp(&id,&explicit_components_[i],sizeof(id)) &&
               !std::memcmp(&sound,&explicit_sounds_[i],sizeof(sound))) return true;
        return false;
    }
    bool protects(uint64_t token) const {
        if(!active()) return false;
        if(state_==2 || token==tokens_[0] || token==tokens_[1]) return true;
        for(unsigned i=0;i<explicit_count_;++i) if(token==explicit_tokens_[i]) return true;
        return false;
    }
    template<class Pool>
    uint32_t create_sound(uint64_t base,uint64_t session,Pool& leases,const CallIdentity& world,
                          RetainedCallPacket& packet,const CallRetention* retention,
                          const CallEntryValidation* entry) {
        auto& c=packet.call;
        if(state_!=1 || !owned_sound_slot_available(explicit_count_) || !owned_sound_factory_contract(c)) return 1494;
        const auto fn=call_identity(base,c.function), factory_target=call_identity(base,c.target);
        const auto cls=fn ? local_read<uint64_t>(fn+0x20) : 0;
        if(!fn || !factory_target || !(local_read<uint32_t>(factory_target+8)&0x10) ||
           local_read<uint64_t>(factory_target+0x10)!=cls || !exact_name(base,fn+0x18,"CreateSound2D") ||
           !exact_name(base,cls+0x18,"GameplayStatics") ||
           !exact_name(base,local_read<uint64_t>(cls+0x20)+0x18,"/Script/Engine")) return 1494;
        for(unsigned i=0;i<c.object_count;++i)
            if(c.objects[i].offset==0 && std::memcmp(&c.objects[i].identity,&world,sizeof(world))) return 1494;
        diagnostic_phase(AudioCleanupPhase::SoundFactory,explicit_count_);
#ifdef E33_AUDIO_CLEANUP_DIAGNOSTICS_SESSION
        diagnostics_.dispatching();
#endif
        state_=2;
        const auto error=reflected_call(base,c,retention,nullptr,nullptr,nullptr,false,entry);
#ifdef E33_AUDIO_CLEANUP_DIAGNOSTICS_SESSION
        diagnostics_.returned(error,c.outcome);
#endif
        if(c.outcome==CallNotDispatched) { state_=1; return error; }
        if(error || c.outcome!=CallDispatchReturned) { diagnostic_failure(1,error,c.outcome);return error ? error : 1493; }
        CallIdentity component{-1,0,0}; uint64_t token=0;
        for(unsigned i=0;i<c.object_count;++i) if(c.objects[i].offset==48) component=c.objects[i].identity;
        for(unsigned i=0;i<packet.count;++i) if(packet.leases[i].offset==48) token=packet.leases[i].token;
        if(!component.address && !packet.count) { state_=1; return 0; }
        if(!call_identity(base,component) || local_read<uint64_t>(component.address+0x10)!=audio_.address ||
           !token || !leases.owns_object(session,token,component.address)) { diagnostic_failure(2,error,c.outcome);return 1493; }
        explicit_components_[explicit_count_]=component;
        for(unsigned i=0;i<c.object_count;++i) if(c.objects[i].offset==8) explicit_sounds_[explicit_count_]=c.objects[i].identity;
        explicit_tokens_[explicit_count_++]=token;
        state_=1; return 0;
    }
    template<class Pool>
    uint32_t close(uint64_t base,uint64_t session,Pool&) {
#ifdef E33_CINEMATIC_EPOCH_RETIRE_SESSION
        if(active()&&epoch_.world.address) {
            e33_retired_world::TargetOps current{base};
            const auto proof=e33_retired_world::double_observe(current,epoch_.world);
            if(retiring_||proof!=e33_retired_world::Result::SameWorld)
                return proof==e33_retired_world::Result::Pending?407:1493;
        }
#endif
#ifdef E33_ORIGINAL_AUDIO_PAUSE_SESSION
        // Restore known original pause changes even if owned audio quarantines.
        if(state_!=2) diagnostic_phase(AudioCleanupPhase::PauseRestore);
        const auto pause_error=original_pause_.close();
#ifdef E33_AUDIO_CLEANUP_DIAGNOSTICS_SESSION
        diagnostics_.pause(pause_error,original_pause_.diagnostic_error());
#endif
        const auto owned_error=close_owned(base,session);
        if(pause_error && !owned_error) {
            diagnostic_phase(AudioCleanupPhase::PauseRestore);
#ifdef E33_AUDIO_CLEANUP_DIAGNOSTICS_SESSION
            diagnostics_.returned(original_pause_.diagnostic_error(),original_pause_.diagnostic_outcome());
            if(pause_error!=407) diagnostics_.failure(pause_error);
#endif
        }
        if(pause_error && !state_) state_=2;
        return owned_error ? owned_error : pause_error;
    }
    uint32_t close_owned(uint64_t base,uint64_t session) {
#endif
        if(!state_) return 0;
        if(state_==2) return 1493;
        diagnostic_phase(AudioCleanupPhase::Context,index_,step_);
        TargetObjectAssignmentOps context{base};
        if(!context.context()) return 407;
        if(state_==1) {
            state_=2;
            MusicAudioReferenceSet<kOwnedAudioCleanupCapacity> current{};
            MusicAudioReferences original_now{};
            uint32_t detail{};
            diagnostic_phase(AudioCleanupPhase::PrivateReferences);
            if(!music_audio_references(base,isolated_,audio_,current,&detail)) {
                diagnostic_counts(0,current.count);diagnostic_failure(detail);return 1493;
            }
            diagnostic_phase(AudioCleanupPhase::OriginalReferences);
            if(!music_audio_references(base,original_,audio_,original_now,&detail)) {
                diagnostic_counts(original_now.count,current.count);diagnostic_failure(detail);return 1493;
            }
            diagnostic_counts(original_now.count,current.count);
            for(unsigned i=0;i<explicit_count_;++i) {
                diagnostic_phase(AudioCleanupPhase::ExplicitIdentity,i);
                if(!call_identity(base,explicit_components_[i]) ||
                   !current.add(base,explicit_components_[i].address,audio_.address)) {
                    diagnostic_failure();return 1493;
                }
            }
            diagnostic_counts(original_now.count,current.count);
            for(unsigned i=0;i<current.count;++i) {
                diagnostic_phase(AudioCleanupPhase::OriginalOverlap,i);
                for(unsigned j=0;j<originals_.count;++j)
                    if(current.items[i].address==originals_.items[j].address) { diagnostic_failure(j+1);return 1493; }
                diagnostic_phase(AudioCleanupPhase::CurrentOverlap,i);
                for(unsigned j=0;j<original_now.count;++j)
                    if(current.items[i].address==original_now.items[j].address) { diagnostic_failure(j+1);return 1493; }
            }
            diagnostic_phase(AudioCleanupPhase::Capacity);
            const auto capacity=component_leases_.preflight(session,current.count);
            if(capacity!=StrongLeaseResult::Ok) { diagnostic_failure(static_cast<uint32_t>(capacity));return 1493; }
            cleanup_=current;
            for(unsigned i=0;i<cleanup_.count;++i) {
                diagnostic_phase(AudioCleanupPhase::Acquire,i);
                TargetStrongReferenceOps ops{base,cleanup_.items[i]};
                const auto acquired=component_leases_.acquire(ops,session,cleanup_.items[i].address,component_tokens_[i]);
                if(acquired!=StrongLeaseResult::Ok) { diagnostic_failure(static_cast<uint32_t>(acquired));return 1493; }
                // A strong holder prevents collection but does not assign a weak
                // serial. Stop/callbacks may mint that serial; stabilize while
                // this exact identity is retained, never refresh a stale token.
                if(!stabilize_retained_identity(ops,cleanup_.items[i])) {
                    diagnostic_failure(2);return 1493;
                }
            }
            index_=step_=0; state_=3;
        }
        while(index_<cleanup_.count) {
            const auto id=cleanup_.items[index_];
            // A callback can destroy another entry. Never call a reused/stale
            // address and never reinterpret it as an unrelated component.
            if(!call_identity(base,id)) { ++index_; step_=0; continue; }
            auto plan=step_ ? destroy_ : stop_;
            plan.target=id;
            if(step_) plan.objects[0].identity=id;
            diagnostic_phase(step_ ? AudioCleanupPhase::Destroy : AudioCleanupPhase::Stop,index_,step_);
            state_=2;
#ifdef E33_AUDIO_CLEANUP_DIAGNOSTICS_SESSION
            diagnostics_.dispatching();
#endif
            uint32_t rejection_detail=0;
            auto error=reflected_call(base,plan,nullptr,nullptr,nullptr,nullptr,false,nullptr,false,nullptr,nullptr,&rejection_detail);
#ifdef E33_AUDIO_CLEANUP_DIAGNOSTICS_SESSION
            diagnostics_.returned(error,plan.outcome);
#endif
            if(error==201 && plan.outcome==CallNotDispatched) { state_=3; return 407; }
#ifdef E33_AUDIO_COMPLETION_SESSION
            if(completed_destroy(base,session,id,component_tokens_[index_],error,plan.outcome,rejection_detail)) {
                // Stop returned and the engine completed logical destruction.
                // Do not dispatch Destroy again; normal guarded holder release
                // below still owns cleanup and can defer/quarantine independently.
                ++index_;step_=0;state_=3;continue;
            }
#endif
            if(error || plan.outcome!=CallDispatchReturned) { diagnostic_failure(rejection_detail ? rejection_detail : 1,error,plan.outcome);return 1493; }
            if(step_) { ++index_; step_=0; } else step_=1;
            state_=3;
        }
        for(unsigned i=0;i<cleanup_.count;++i) if(component_tokens_[i]) {
            diagnostic_phase(AudioCleanupPhase::Release,i);
            TargetStrongReferenceOps ops{base,cleanup_.items[i]};
            auto result=component_leases_.release(ops,session,component_tokens_[i]);
            if(result==StrongLeaseResult::Deferred) return 407;
            if(result!=StrongLeaseResult::Ok) { diagnostic_failure(static_cast<uint32_t>(result));state_=2; return 1493; }
            component_tokens_[i]=0;
        }
        TargetStrongReferenceOps release_ops{base,{}};
        diagnostic_phase(AudioCleanupPhase::ClosePool);
        const auto closed=component_leases_.close(release_ops,session);
        if(closed!=StrongLeaseResult::Ok) {
            diagnostic_failure(static_cast<uint32_t>(closed));
            state_=2; return 1493;
        }
        diagnostic_phase(AudioCleanupPhase::Complete);state_=0; return 0;
    }
#ifdef E33_CINEMATIC_EPOCH_RETIRE_SESSION
    uint32_t current_state()const{return state_;}
    const e33_retired_world::Snapshot& captured_epoch()const{return epoch_;}
    template<class Pool,class Reference>
    uint32_t retire_world(uint64_t base,uint64_t session,Pool&,const e33_retired_world::Snapshot& source,
                          Reference& reference,uint64_t source_menu_owner) {
        if(!active()&&!reference.active())return 0;
        if(!source_menu_owner||source_menu_owner!=menu_owner_||state_==2||!epoch_.world.address||!e33_retired_world::same(source.world,epoch_.world))return 1493;
        e33_retired_world::TargetOps current{base};
        const auto proof=e33_retired_world::double_observe(current,epoch_.world);
        if(proof!=e33_retired_world::Result::Retired)return proof==e33_retired_world::Result::Pending?407:1493;
        retiring_=true;
        // Only current persistent GI state is eligible for compensation. A new
        // GI or a foreign replacement is preserved by the reference owner.
        const auto restored=reference.retire_music_reference(base,epoch_,gi_,original_,isolated_,audio_);
        if(restored) {if(restored!=407)state_=2;return restored;}
#ifdef E33_ORIGINAL_AUDIO_PAUSE_SESSION
        auto certificate=[&](const CallIdentity& component) {
            return e33_cinematic::current_original_audio(base,gi_,original_,audio_,component);
        };
        const auto paused=original_pause_.retire_world(epoch_,certificate);
        if(paused) {if(paused!=407)state_=2;return paused;}
#endif
        // No old-world Stop/Destroy, private-container walk or callback. World
        // teardown owns those components; release only our private collectors.
        TargetStrongReferenceOps refs{base,{}};
        const auto released=release_retired_collectors(component_leases_,refs,session);
        if(released!=StrongLeaseResult::Ok) {
            if(released!=StrongLeaseResult::Deferred)state_=2;
            return released==StrongLeaseResult::Deferred?407:1493;
        }
        std::memset(component_tokens_,0,sizeof(component_tokens_));
        state_=0;return 0;
    }
    template<class Pool,class Reference>
    void retire_command(uint64_t base,uint64_t session,Pool&leases,Reference&reference,MusicAudioOwnerPacket&p) {
        const auto* bytes=reinterpret_cast<const uint8_t*>(&p.original);
        bool payload=false;for(size_t i=0;i<sizeof(p)-32;++i)payload|=bytes[i]!=0;
        if(p.version!=1||p.operation!=5||p.owner!=owner_||p.reserved||p.error||p.state||payload) {p.error=1491;return;}
        p.error=retire_world(base,session,leases,epoch_,reference,menu_owner_);p.state=state_;
    }
#endif
    template<class Pool>
    void command(uint64_t base,uint64_t session,Pool& leases,bool menu_active,MusicAudioOwnerPacket& p,
                 const CallIdentity* controller=nullptr,uint64_t menu_owner=0) {
        const uint32_t max_operation=
#ifdef E33_ORIGINAL_AUDIO_PAUSE_SESSION
            4;
#else
            3;
#endif
        if(p.version!=1 || !p.owner || p.reserved || p.error || p.state || p.operation<1 || p.operation>max_operation) {
            p.error=1490; return;
        }
        p.state=state_;
#ifdef E33_ORIGINAL_AUDIO_PAUSE_SESSION
        if(p.operation==4) {
            const auto* prefix=reinterpret_cast<const uint8_t*>(&p.original);
            const auto* tail=reinterpret_cast<const uint8_t*>(&p.destroy);
            for(size_t i=0;i<64;++i) if(prefix[i]) { p.error=1512; return; }
            for(size_t i=0;i<sizeof(p.destroy);++i) if(tail[i]) { p.error=1512; return; }
            if(p.owner!=owner_ || state_!=1 || !menu_active) { p.error=1512; return; }
            MusicAudioReferences now{};
            if(!music_audio_references(base,original_,audio_,now)) { p.error=1512; return; }
            p.error=original_pause_.open(base,session,audio_,now,p.stop);
            return;
        }
#endif
        if(p.operation!=1) {
            const auto* bytes=reinterpret_cast<const uint8_t*>(&p.original);
            for(size_t i=0;i<sizeof(p)-32;++i) if(bytes[i]) { p.error=1491; return; }
            if(p.owner!=owner_) { p.error=1491; return; }
            if(p.operation==2) p.error=close(base,session,leases);
            p.state=state_; return;
        }
        if(active() || !menu_active || p.original.address==p.isolated.address ||
           !leases.owns_object(session,p.original_token,p.original.address) ||
           !leases.owns_object(session,p.isolated_token,p.isolated.address)) { p.error=1491; return; }
        MusicAudioReferences original_refs{}, isolated{};
        if(!music_audio_references(base,p.original,p.audio_class,original_refs) ||
           !music_audio_references(base,p.isolated,p.audio_class,isolated) || isolated.count) { p.error=1492; return; }
#ifdef E33_CINEMATIC_EPOCH_RETIRE_SESSION
        e33_retired_world::Snapshot epoch{};CallIdentity gi{};e33_retired_world::TargetOps current{base};
        if(!menu_owner||!controller||!e33_cinematic::current_music_gi(base,epoch,gi)||epoch.world.serial<=0||
           !current.controller_world(*controller,epoch.world)||
           local_read<uint64_t>(p.original.address+32)!=gi.address||
           local_read<uint64_t>(p.isolated.address+32)!=gi.address) {p.error=1492;return;}
#else
        (void)controller;(void)menu_owner;
#endif
        const CallPacket* plans[]={&p.stop,&p.destroy};
        for(unsigned i=0;i<2;++i) {
            auto c=*plans[i];
            const auto fn=call_identity(base,c.function), obj=call_identity(base,c.target);
            const auto cls=fn ? local_read<uint64_t>(fn+0x20) : 0;
            if(validate_call_packet(c) || !fn || !obj || !(local_read<uint32_t>(obj+8)&0x10) ||
               local_read<uint64_t>(obj+0x10)!=p.audio_class.address ||
               !exact_name(base,fn+0x18,i ? "K2_DestroyComponent" : "Stop") ||
               !exact_name(base,cls+0x18,i ? "ActorComponent" : "AudioComponent") ||
               !exact_name(base,local_read<uint64_t>(cls+0x20)+0x18,"/Script/Engine") ||
               c.entry_rva!=(i ? 0x353a100u : 0x353c7f0u) ||
               c.parameter_size!=(i ? 8u : 0u) || c.return_offset!=65535 ||
               c.field_count!=i || c.object_count!=i ||
               (i && (c.objects[0].offset || c.objects[0].identity.address!=obj ||
                       std::strcmp(c.fields[0].name,"Object") || c.fields[0].kind!=CallObject)) ||
               reflected_call(base,c,nullptr,nullptr,nullptr,nullptr,true)) { p.error=1492; return; }
        }
        if(component_leases_.begin(session)!=StrongLeaseResult::Ok) { p.error=1491; return; }
        original_=p.original; isolated_=p.isolated; audio_=p.audio_class;
        originals_=original_refs; cleanup_={}; stop_=p.stop; destroy_=p.destroy;
        explicit_count_=0;
        tokens_[0]=p.original_token; tokens_[1]=p.isolated_token;
        owner_=p.owner; index_=step_=0; state_=p.state=1;
#ifdef E33_CINEMATIC_EPOCH_RETIRE_SESSION
        epoch_=epoch;gi_=gi;menu_owner_=menu_owner;retiring_=false;
#endif
#ifdef E33_AUDIO_CLEANUP_DIAGNOSTICS_SESSION
        diagnostics_.reset();diagnostic_counts(0,0);
#endif
    }
};
