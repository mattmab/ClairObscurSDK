#pragma once
#include "menu_lifetime.h"

// One bounded menu owner per native session. Preparation itself is durable:
// capture can acquire a Slate reference before MenuLifetime is registered.
class MenuSession {
    uint64_t session_=0, owner_=0, widget_=0, child_=0;
    bool preparing_=false, quarantined_=false, closing_=false;
#ifdef E33_RETIRED_WORLD_SESSION
    bool epoch_release_pending_=false;
#endif
    MenuLifetime lifetime_;
public:
    bool active() const { return session_!=0; }
    void stop_actions() { if(active()) closing_=true; }
    bool accepts_actions() const {
        return active() && !preparing_ && !quarantined_ && !closing_ &&
            (lifetime_.state()==MenuState::Attached || lifetime_.state()==MenuState::Focused);
    }
    bool protects(uint64_t session,uint64_t token) const {
        return active() && session==session_ && token && (token==widget_ || token==child_);
    }
    void quarantine() { if(active()) quarantined_=true; }
    template<class Ops> MenuResult close(Ops& ops,uint64_t session,uint64_t owner) {
        if(!active()) return MenuResult::Ok;
        if(session!=session_ || owner!=owner_) return MenuResult::Invalid;
        closing_=true;
        if(quarantined_) return MenuResult::Quarantined;
#ifdef E33_RETIRED_WORLD_SESSION
        auto result=epoch_release_pending_ ? MenuResult::Ok :
            (preparing_ ? ops.release_prepared_baseline() : lifetime_.close(ops,session_,owner_));
        if(result==MenuResult::Ok){
            epoch_release_pending_=true;result=ops.release_epoch_anchor();
            if(result==MenuResult::Ok)epoch_release_pending_=false;
        }
#else
        auto result=preparing_ ? ops.release_prepared_baseline() : lifetime_.close(ops,session_,owner_);
#endif
        if(result==MenuResult::Ok) {
            session_=owner_=widget_=child_=0; preparing_=false; closing_=false;
        } else if(result!=MenuResult::Deferred) quarantined_=true;
        return result;
    }
    template<class Ops> MenuResult close_session(Ops& ops) {
        return close(ops,session_,owner_);
    }
    template<class Ops> MenuResult prepare(Ops& ops,uint64_t session,uint64_t owner,
                                         uint64_t widget,uint64_t child) {
        if(active()) return MenuResult::Busy;
        if(!session || !owner || !widget || !child || widget==child ||
           !ops.validate_preparation(session,owner,widget,child)) return MenuResult::Invalid;
        session_=session; owner_=owner; widget_=widget; child_=child; preparing_=true;
        auto result=ops.capture_baseline();
        if(result==MenuResult::Ok) {
            result=lifetime_.register_owned(ops,session,owner,widget,child);
            if(result==MenuResult::Ok) { preparing_=false; return result; }
        }
        auto cleaned=close_session(ops);
        return cleaned==MenuResult::Ok ? result : cleaned;
    }
    template<class Ops> MenuResult attach(Ops& ops,uint64_t session,uint64_t owner) {
        if(quarantined_ || preparing_) return MenuResult::Busy;
#ifdef E33_RETIRED_WORLD_SESSION
        const auto ready=ops.admit_world_actions();if(ready!=MenuResult::Ok)return ready;
#endif
        return lifetime_.attach(ops,session,owner);
    }
    template<class Ops> MenuResult focus(Ops& ops,uint64_t session,uint64_t owner) {
        if(quarantined_ || preparing_) return MenuResult::Busy;
#ifdef E33_RETIRED_WORLD_SESSION
        const auto ready=ops.admit_world_actions();if(ready!=MenuResult::Ok)return ready;
#endif
        return lifetime_.focus(ops,session,owner);
    }
};
