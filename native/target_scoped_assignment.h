#pragma once
#include "scoped_assignment.h"
#include "scoped_assignment_protocol.h"
#include "target_object_assignment.h"
#ifdef E33_CINEMATIC_EPOCH_RETIRE_SESSION
#include "cinematic_current_music.h"
#endif

class TargetScopedAssignment {
    ScopedAssignment state_;
    uint64_t owner_=0,tokens_[3]{};
#ifdef E33_CINEMATIC_EPOCH_RETIRE_SESSION
    e33_retired_world::Snapshot music_epoch_{};
#endif
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
#ifdef E33_CINEMATIC_EPOCH_RETIRE_SESSION
        if(active()&&music_epoch_.world.address) {
            e33_retired_world::TargetOps current{base};
            const auto proof=e33_retired_world::double_observe(current,music_epoch_.world);
            if(proof!=e33_retired_world::Result::SameWorld)
                return proof==e33_retired_world::Result::Pending ? 407 : 1483;
        }
#endif
        TargetObjectAssignmentOps ops{base};
        auto result=state_.close(ops);
        if(result==ObjectAssignmentResult::Ok) return 0;
        return result==ObjectAssignmentResult::InvalidContext && state_.state()==1 ? 407 : 1483;
    }
#ifdef E33_CINEMATIC_EPOCH_RETIRE_SESSION
    uint32_t retire_music_reference(uint64_t base,const e33_retired_world::Snapshot& epoch,
            const CallIdentity& gi,const CallIdentity& original_system,const CallIdentity& isolated,
            const CallIdentity& audio) {
        if(!active())return 0;
        if(state_.state()!=1||!e33_retired_world::same(music_epoch_.world,epoch.world))return 1483;
        e33_retired_world::TargetOps current{base};
        const auto proof=e33_retired_world::double_observe(current,epoch.world);
        if(proof!=e33_retired_world::Result::Retired)return proof==e33_retired_world::Result::Pending?407:1483;
        const auto& restore=state_.restore();
        if(std::strcmp(restore.name,"InteractiveMusicSystem")||
           !e33_retired_world::same(restore.target,gi)||!e33_retired_world::same(restore.expected,isolated)||
           !e33_retired_world::same(restore.value,original_system))return 1483;
        e33_retired_world::Snapshot now{};CallIdentity current_gi{};
        if(!e33_cinematic::current_music_gi(base,now,current_gi))return 407;
        if(!e33_retired_world::same(current_gi,gi))return state_.abandon_retired_owner()?0:1483;
        TargetObjectAssignmentOps assignment{base};
        if(!assignment.context())return 407;
        const auto property=assignment.validate(restore);
        if(!property)return 1483;
        if(assignment.read(restore)!=isolated.address)return state_.abandon_retired_owner()?0:1483;
        MusicAudioReferences original_now{};
        if(!current.live(original_system.address)||!music_audio_references(base,original_system,audio,original_now))return 1483;
        const auto result=state_.close(assignment);
        if(result!=ObjectAssignmentResult::Ok)return result==ObjectAssignmentResult::InvalidContext?407:1483;
        e33_retired_world::Snapshot after{};CallIdentity after_gi{};
        return e33_cinematic::current_music_gi(base,after,after_gi)&&
            e33_retired_world::same(now.world,after.world)&&e33_retired_world::same(gi,after_gi)&&
            zone_ref(base,gi.address,"InteractiveMusicSystem")==original_system.address ? 0 : 1483;
    }
#endif
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
#ifdef E33_CINEMATIC_EPOCH_RETIRE_SESSION
        music_epoch_={};
        if(!std::strcmp(a.name,"InteractiveMusicSystem")) {
            CallIdentity current_gi{};
            if(!e33_cinematic::current_music_gi(base,music_epoch_,current_gi)||
               music_epoch_.world.serial<=0||!e33_retired_world::same(current_gi,a.target)) {p.error=1481;return;}
        }
#endif
        auto result=state_.open(ops,a);
        p.state=state_.state();
        p.error=result==ObjectAssignmentResult::Ok ? 0 : 1482;
    }
};
