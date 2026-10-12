#pragma once
#include "cinematic_widget_journal.h"

namespace e33_cinematic {
enum class AnimationQuiescence { pending, complete, uncertain };
// One exact owned widget/animation/player tuple; identities and retention are
// supplied by the native adapter. No ABI or guessed engine field is used here.
// Deferred mutation means provably NOT dispatched; a returned stop can still
// require later game-thread polls before completion and release are safe.
class AnimationDrain {
    enum State { ready, unbinding, stopping, draining, complete, uncertain } state_=ready;
public:
    bool finished() const { return state_==complete; }
    bool quarantined() const { return state_==uncertain; }
    template<class Ops>
    WidgetStep close(Ops& ops) {
        if(state_==complete) return WidgetStep::ok;
        if(state_==uncertain) return WidgetStep::uncertain;
        if(state_==ready) state_=unbinding;
        if(state_==unbinding) {
            state_=uncertain;
            const auto result=ops.unbind_finished();
            if(result==WidgetStep::deferred) { state_=unbinding;return result; }
            if(result!=WidgetStep::ok) return WidgetStep::uncertain;
            state_=stopping;
        }
        if(state_==stopping) {
            state_=uncertain;
            const auto result=ops.stop();
            if(result==WidgetStep::deferred) { state_=stopping;return result; }
            if(result!=WidgetStep::ok) return WidgetStep::uncertain;
            state_=draining;
        }
        state_=uncertain;
        const auto result=ops.quiescence();
        if(result==AnimationQuiescence::pending) { state_=draining;return WidgetStep::deferred; }
        if(result!=AnimationQuiescence::complete) return WidgetStep::uncertain;
        state_=complete;return WidgetStep::ok;
    }
};
}
