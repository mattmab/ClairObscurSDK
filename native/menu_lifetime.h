#pragma once
#include <cstdint>

enum class MenuContext { Ready, Deferred, Terminal };
enum class MenuFocusOwner { Owned, Prior, Unrelated, Invalid };
enum class MenuResult { Ok, Invalid, Busy, Deferred, Quarantined };
enum class MenuState {
    Empty, Registered, AttachUnknown, Attached, FocusUnknown, Focused,
    RestorePending, RestoreUnknown, DeactivatePending, DeactivateUnknown,
    DetachPending, DetachUnknown, ReleasePending, ReleaseUnknown, Quarantined
};

// Durable native bookkeeping, independent of IPC/Python memory. The target
// adapter must own its captured restoration data and verify all object leases.
// This record protects existing leases; it does not allocate or release them.
// Runtime integration MUST consult protects() for explicit lease release and
// finish close() before releasing the pool on controller loss.
class MenuLifetime {
    MenuState state_=MenuState::Empty;
    uint64_t session_=0, owner_=0, widget_=0, child_=0;

    bool matches(uint64_t session,uint64_t owner) const {
        return session && owner && session==session_ && owner==owner_;
    }
    MenuResult quarantine() { state_=MenuState::Quarantined; return MenuResult::Quarantined; }
    template<class Ops> MenuResult context(Ops& ops) {
        switch(ops.context()) {
        case MenuContext::Ready: return MenuResult::Ok;
        case MenuContext::Deferred: return MenuResult::Deferred;
        default: return quarantine();
        }
    }
    void clear() { state_=MenuState::Empty; session_=owner_=widget_=child_=0; }
public:
    MenuLifetime()=default;
    MenuLifetime(const MenuLifetime&)=delete;
    MenuLifetime& operator=(const MenuLifetime&)=delete;
    MenuState state() const { return state_; }
    bool active() const { return state_!=MenuState::Empty; }
    bool protects(uint64_t session,uint64_t lease) const {
        return active() && session==session_ && lease && (lease==widget_ || lease==child_);
    }
    template<class Ops>
    MenuResult register_owned(Ops& ops,uint64_t session,uint64_t owner,
                              uint64_t widget_lease,uint64_t child_lease) {
        if(active()) return MenuResult::Busy;
        if(!session || !owner || !widget_lease || !child_lease || widget_lease==child_lease)
            return MenuResult::Invalid;
        if(ops.context()!=MenuContext::Ready) return MenuResult::Invalid;
        // Read-only validation: no engine ownership acquisition or mutation.
        if(!ops.validate_owned(session,owner,widget_lease,child_lease)) return MenuResult::Invalid;
        session_=session; owner_=owner; widget_=widget_lease; child_=child_lease;
        state_=MenuState::Registered;
        return MenuResult::Ok;
    }
    template<class Ops> MenuResult attach(Ops& ops,uint64_t session,uint64_t owner) {
        if(!matches(session,owner)) return MenuResult::Invalid;
        if(state_!=MenuState::Registered) return MenuResult::Busy;
        auto ready=context(ops); if(ready!=MenuResult::Ok) return ready;
        state_=MenuState::AttachUnknown;
        // Adapter performs and verifies attachment; a fault cannot be replayed.
        if(!ops.attach()) return quarantine();
        state_=MenuState::Attached;
        return MenuResult::Ok;
    }
    template<class Ops> MenuResult focus(Ops& ops,uint64_t session,uint64_t owner) {
        if(!matches(session,owner)) return MenuResult::Invalid;
        if(state_!=MenuState::Attached) return MenuResult::Busy;
        auto ready=context(ops); if(ready!=MenuResult::Ok) return ready;
        if(!ops.prior_target_valid()) return MenuResult::Invalid;
        state_=MenuState::FocusUnknown;
        if(!ops.focus()) {
#ifdef E33_VIEWER_MENU_SESSION
            if(ops.recover_focus()) {state_=MenuState::Attached;return MenuResult::Invalid;}
#endif
            return quarantine();
        }
        state_=MenuState::Focused;
        return MenuResult::Ok;
    }
    template<class Ops> MenuResult close(Ops& ops,uint64_t session,uint64_t owner) {
        if(!matches(session,owner)) return MenuResult::Invalid;
        switch(state_) {
        case MenuState::AttachUnknown: case MenuState::FocusUnknown:
        case MenuState::RestoreUnknown: case MenuState::DeactivateUnknown:
        case MenuState::DetachUnknown: case MenuState::ReleaseUnknown: case MenuState::Quarantined:
            return quarantine();
        default: break;
        }
        auto ready=context(ops); if(ready!=MenuResult::Ok) return ready;
        if(state_==MenuState::Registered) state_=MenuState::ReleasePending;
        if(state_==MenuState::Attached || state_==MenuState::Focused) {
            // Attachment/activation can move focus even before focus() runs.
            switch(ops.focus_owner()) {
            case MenuFocusOwner::Owned: state_=MenuState::RestorePending; break;
            case MenuFocusOwner::Prior: case MenuFocusOwner::Unrelated:
                state_=MenuState::DeactivatePending; break;
            default: return quarantine();
            }
        }
        if(state_==MenuState::RestorePending) {
            ready=context(ops); if(ready!=MenuResult::Ok) return ready;
            // Deferred cleanup must reobserve focus rather than steal it back.
            auto current=ops.focus_owner();
            if(current==MenuFocusOwner::Invalid) return quarantine();
            if(current==MenuFocusOwner::Owned) {
                if(!ops.prior_target_valid()) return quarantine();
                state_=MenuState::RestoreUnknown;
                if(!ops.restore()) return quarantine();
            }
            state_=MenuState::DeactivatePending;
        }
        if(state_==MenuState::DeactivatePending) {
            ready=context(ops); if(ready!=MenuResult::Ok) return ready;
            state_=MenuState::DeactivateUnknown;
            if(!ops.deactivate()) return quarantine();
            state_=MenuState::DetachPending;
        }
        if(state_==MenuState::DetachPending) {
            ready=context(ops); if(ready!=MenuResult::Ok) return ready;
            state_=MenuState::DetachUnknown;
            if(!ops.detach()) return quarantine();
            state_=MenuState::ReleasePending;
        }
        if(state_==MenuState::ReleasePending) {
            ready=context(ops); if(ready!=MenuResult::Ok) return ready;
#ifdef E33_RETIRED_WORLD_SESSION
            const auto released=ops.release_baseline_result();
            if(released==MenuResult::Deferred)return released;
            if(released!=MenuResult::Ok)return quarantine();
#else
            state_=MenuState::ReleaseUnknown;
            if(!ops.release_baseline()) return quarantine();
#endif
            clear();
            return MenuResult::Ok;
        }
        return MenuResult::Busy;
    }
};
