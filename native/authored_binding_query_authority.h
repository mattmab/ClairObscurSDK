#pragma once
#include "bound_object_frame.h"

namespace e33_authored_binding {
// Research-only admission journal. The resolver callback must perform the
// engine GetPortableBindingID operation with its own durable native frame and
// retained identities; a wire-supplied sequence ID is never an authority.
// This journal does not dispatch GetBoundObjects or acquire UObject leases.
template<class Identity>
class Authority {
    uint64_t session_=0;
    Identity player_{},actor_{},root_{},source_{};
    e33_camera_binding::BindingValue binding_{};
    bool active_=false,uncertain_=false;
    uint32_t rejection_stage_=0;
public:
    bool active()const{return active_;}
    bool uncertain()const{return uncertain_;}
    uint32_t rejection_stage()const{return rejection_stage_;}
    // This value originates only from the native resolver.  It is valid while
    // the authority remains active and must still be checked through matches
    // immediately before and after every engine dispatch.
    const e33_camera_binding::BindingValue* value()const {
        return active_ && !uncertain_ ? &binding_ : nullptr;
    }
    template<class Ops>
    bool derive(Ops& ops,uint64_t session,const Identity& player,const Identity& actor,
                const Identity& root,const Identity& source,const uint32_t (&guid)[4]) {
        rejection_stage_=0;
        if(active_ || uncertain_ || !session || !(guid[0]||guid[1]||guid[2]||guid[3]) || !ops.context()) {rejection_stage_=1;return false;}
        if(!ops.owned_player(session,player,actor,root)) {rejection_stage_=2;return false;}
        if(!ops.unique_reachable_source(session,root,source)) {rejection_stage_=3;return false;}
        if(!ops.authored_binding(session,source,guid)) {rejection_stage_=4;return false;}
        // Publish uncertainty before the engine query. Unknown/partial dispatch
        // may never be retried or replaced with a caller-supplied root ID.
        uncertain_=true;
        e33_camera_binding::BindingValue observed{};
        const auto result=ops.resolve(session,root,source,guid,observed);
        if(result==e33_camera_binding::QueryResult::rejected) {uncertain_=false;rejection_stage_=5;return false;}
        if(result!=e33_camera_binding::QueryResult::ok ||
           std::memcmp(observed.guid,guid,sizeof(observed.guid)) || !ops.context() ||
           !ops.owned_player(session,player,actor,root) ||
           !ops.unique_reachable_source(session,root,source) ||
           !ops.authored_binding(session,source,guid))return false;
        player_=player;actor_=actor;root_=root;source_=source;binding_=observed;
        session_=session;active_=true;uncertain_=false;return true;
    }
    template<class Ops>
    bool matches(Ops& ops,uint64_t session,const Identity& player,const Identity& actor,
                 const Identity& root,const e33_camera_binding::BindingValue& binding)const {
        return active_ && !uncertain_ && session==session_ && ops.context() &&
            ops.same(player_,player) && ops.same(actor_,actor) && ops.same(root_,root) &&
            !std::memcmp(&binding_,&binding,sizeof(binding_)) &&
            ops.owned_player(session,player,actor,root) &&
            ops.unique_reachable_source(session,root,source_) &&
            ops.authored_binding(session,source_,binding_.guid);
    }
    template<class Ops> bool clear(Ops& ops) {
        if(uncertain_ || !ops.context() || !ops.outputs_released())return false;
        *this={};return true;
    }
};
}
