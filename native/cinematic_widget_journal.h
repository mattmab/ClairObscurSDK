#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

namespace e33_cinematic {
// Native ownership journal, independent of Blueprint frame parsing. Ops supplies
// validated identity, strong retention and one RemoveFromParent dispatch.
// Every entry is published before retention; uncertain mutations quarantine.
enum class WidgetStep { ok, deferred, uncertain };
template<class Identity, size_t Capacity=16>
class WidgetJournal {
    struct Entry { Identity track{},widget{}; uint64_t track_token{},widget_token{}; bool detached=false; };
    std::array<Entry,Capacity> entries_{};
    size_t count_=0, detach_=0;
    enum State { idle, active, draining, uncertain, releasing } state_=idle;
public:
    bool active_owner() const { return state_!=idle; }
    bool quarantined() const { return state_==uncertain; }
    size_t count() const { return count_; }
    bool begin() { if(state_!=idle) return false; state_=active; return true; }
    template<class Ops>
    bool owns_track(Ops& ops,const Identity& track) const {
        // Recognition survives quarantine: a later InputRemoved must never
        // fall through to the gameplay component after Inputs has been cleared.
        if(state_==idle) return false;
        for(size_t i=0;i<count_;++i)
            if(ops.same(entries_[i].track,track) && ops.valid(entries_[i].track)) return true;
        return false;
    }
    template<class Ops>
    bool admit(Ops& ops,Identity track,Identity widget) {
        if(state_!=active || !ops.valid(track) || !ops.valid(widget)) return false;
        for(size_t i=0;i<count_;++i)
            if(ops.same(entries_[i].track,track) && ops.same(entries_[i].widget,widget)) return true;
        if(count_==Capacity || !ops.capacity(2)) return false;
        auto& item=entries_[count_++]; item.track=track; item.widget=widget;
        state_=uncertain;
        if(!ops.retain(item.track,item.track_token) || !ops.retain(item.widget,item.widget_token)) return false;
        state_=active; return true;
    }
    // Call only after the owning sequence has stopped. A deferred detach has
    // provably not dispatched; uncertain calls must not be repeated.
    template<class Ops>
    WidgetStep close(Ops& ops) {
        if(state_==idle) return WidgetStep::ok;
        if(state_==uncertain) return WidgetStep::uncertain;
        if(state_==active) state_=draining;
        if(state_==draining) {
            while(detach_<count_) {
                auto& item=entries_[detach_];
                if(!item.detached && ops.valid(item.widget)) {
                    state_=uncertain;
                    const auto result=ops.detach(item.widget);
                    if(result==WidgetStep::deferred) { state_=draining; return result; }
                    if(result!=WidgetStep::ok) return WidgetStep::uncertain;
                    state_=draining;
                }
                item.detached=true; ++detach_;
            }
            state_=releasing;
        }
        state_=uncertain;
        const auto released=ops.release_all();
        if(released==WidgetStep::deferred) { state_=releasing; return released; }
        if(released!=WidgetStep::ok) return WidgetStep::uncertain;
        entries_={};count_=detach_=0;state_=idle;return WidgetStep::ok;
    }
};
}
