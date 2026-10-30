#pragma once
#include <cstdint>

namespace e33_camera {
enum class Result { ok, deferred, rejected, unknown };
// One controller, one original target, one positively owned camera. No timer,
// global lookup, borrowed pointer, or arbitrary target can establish ownership.
template<class Identity>
class Journal {
    Identity controller_{}, original_{}, owned_{};
    enum State { idle, captured, playing, restoring, releasing, uncertain } state_=idle;
    bool owns_camera_=false;
public:
    bool ready() const {return state_==captured;}
    bool active() const { return state_!=idle; }
    bool quarantined() const { return state_==uncertain; }
    template<class Ops> Result arm(Ops& ops,const Identity& controller) {
        if(active()) return Result::rejected;
        // Publish before any acquisition; a fault cannot silently forget holds.
        state_=uncertain; controller_=controller;
        const auto result=ops.capture(controller_,original_);
        if(result!=Result::ok) {
            if(result==Result::rejected) {state_=idle;controller_={};}
            return result;
        }
        state_=captured; return Result::ok;
    }
    bool created() { if(state_!=captured) return false;state_=playing;return true; }
    template<class Ops> Result retire(Ops& ops,bool positively_retired) {
        if(!positively_retired) return Result::rejected;
        if(state_==idle) return Result::ok;
        if(state_==uncertain || state_==restoring) return Result::unknown;
        if(!ops.context()) return Result::deferred;
        // Never read or restore the old camera/view target. The game owns old
        // World destruction; only our private collector storage is released.
        state_=uncertain;
        const auto result=ops.release();
        if(result==Result::deferred){state_=releasing;return result;}
        if(result!=Result::ok){state_=uncertain;return Result::unknown;}
        state_=idle;controller_={};original_={};owned_={};owns_camera_=false;
        return Result::ok;
    }
    template<class Ops> Result admit_owned(Ops& ops,const Identity& camera) {
        if(state_!=playing || owns_camera_ || !ops.proven_owned(camera)) return Result::rejected;
        state_=uncertain;
        if(!ops.retain_owned(camera)) return Result::unknown;
        owned_=camera; owns_camera_=true;state_=playing;return Result::ok;
    }
    template<class Ops> Result close(Ops& ops) {
        if(state_==idle) return Result::ok;
        if(state_==uncertain || state_==restoring) return Result::unknown;
        if(!ops.context()) return Result::deferred;
        if(state_==playing) {
            // Must be called after the owned sequence Stop returned.
            Identity current{};
            const auto read=ops.current(controller_,current);
            if(read==Result::deferred) return read;
            if(read!=Result::ok) {state_=uncertain;return Result::unknown;}
            if(!ops.same(current,original_)) {
                if(!owns_camera_ || !ops.same(current,owned_) || !ops.proven_owned(owned_)) {
                    state_=uncertain; return Result::unknown;
                }
                state_=restoring; // Unknown dispatch is never retried.
                const auto restored=ops.restore(controller_,original_);
                if(restored==Result::deferred) {state_=playing;return restored;}
                if(restored!=Result::ok) {state_=uncertain;return Result::unknown;}
            }
        }
        state_=releasing;
        const auto released=ops.release();
        if(released==Result::deferred) return released;
        if(released!=Result::ok) {state_=uncertain;return Result::unknown;}
        state_=idle;controller_={};original_={};owned_={};owns_camera_=false;
        return Result::ok;
    }
};
}
