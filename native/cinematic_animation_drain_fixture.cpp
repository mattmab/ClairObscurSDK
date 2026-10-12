#include "cinematic_animation_drain.h"
#include <cassert>
#include <functional>
#include <iostream>
#include <stdexcept>
using namespace e33_cinematic;
struct Ops {
    unsigned unbound=0,stopped=0,polled=0;
    WidgetStep unbind_result=WidgetStep::ok,stop_result=WidgetStep::ok;
    AnimationQuiescence drain_result=AnimationQuiescence::pending;
    std::function<void()> on_unbind,on_stop,on_poll;
    WidgetStep unbind_finished() { ++unbound;if(on_unbind) on_unbind();return unbind_result; }
    WidgetStep stop() { assert(unbound);++stopped;if(on_stop) on_stop();return stop_result; }
    AnimationQuiescence quiescence() { assert(stopped);++polled;if(on_poll) on_poll();return drain_result; }
};
struct JournalOps : Ops {
    AnimationDrain drain;
    unsigned retained=0,removed=0,released=0;
    bool valid(uint64_t id) const { return id!=0; }
    bool same(uint64_t a,uint64_t b) const { return a==b; }
    bool capacity(uint32_t n) const { return retained+n<=2; }
    bool retain(uint64_t&,uint64_t& token) { token=++retained;return true; }
    WidgetStep detach(uint64_t) {
        const auto result=drain.close(*this);
        if(result!=WidgetStep::ok) return result;
        ++removed;return WidgetStep::ok;
    }
    WidgetStep release_all() { assert(drain.finished() && removed==1);++released;return WidgetStep::ok; }
};
int main() {
    {
        AnimationDrain drain;Ops ops;
        assert(drain.close(ops)==WidgetStep::deferred);
        // A returned StopAnimation is not proof queued completion has drained.
        for(unsigned n=0;n<5;++n) assert(drain.close(ops)==WidgetStep::deferred);
        assert(ops.unbound==1 && ops.stopped==1 && ops.polled==6);
        ops.drain_result=AnimationQuiescence::complete;
        assert(drain.close(ops)==WidgetStep::ok);assert(drain.finished());
        assert(drain.close(ops)==WidgetStep::ok && ops.polled==7);
    }
    {
        AnimationDrain drain;Ops ops;ops.unbind_result=WidgetStep::deferred;
        assert(drain.close(ops)==WidgetStep::deferred && ops.stopped==0);
        ops.unbind_result=WidgetStep::ok;ops.stop_result=WidgetStep::deferred;
        assert(drain.close(ops)==WidgetStep::deferred && ops.polled==0);
        ops.stop_result=WidgetStep::ok;ops.drain_result=AnimationQuiescence::complete;
        assert(drain.close(ops)==WidgetStep::ok && ops.unbound==2 && ops.stopped==2);
    }
    for(unsigned fault=0;fault<3;++fault) {
        AnimationDrain drain;Ops ops;
        if(fault==0) ops.unbind_result=WidgetStep::uncertain;
        if(fault==1) ops.stop_result=WidgetStep::uncertain;
        if(fault==2) ops.drain_result=AnimationQuiescence::uncertain;
        assert(drain.close(ops)==WidgetStep::uncertain && drain.quarantined());
        const auto calls=ops.unbound+ops.stopped+ops.polled;
        assert(drain.close(ops)==WidgetStep::uncertain);
        assert(calls==ops.unbound+ops.stopped+ops.polled);
    }
    {
        AnimationDrain drain;Ops ops;
        const auto nested=[&] { assert(drain.close(ops)==WidgetStep::uncertain); };
        ops.on_unbind=nested;ops.on_stop=nested;ops.on_poll=nested;
        ops.drain_result=AnimationQuiescence::complete;
        assert(drain.close(ops)==WidgetStep::ok);
    }
    {
        AnimationDrain drain;Ops ops;
        ops.on_stop=[] { throw std::runtime_error("injected uncertain dispatch"); };
        try { drain.close(ops);assert(false); } catch(const std::runtime_error&) {}
        assert(drain.quarantined());assert(drain.close(ops)==WidgetStep::uncertain);
        assert(ops.unbound==1 && ops.stopped==1 && ops.polled==0);
    }
    {
        WidgetJournal<uint64_t,1> journal;JournalOps ops;assert(journal.begin());
        assert(journal.admit(ops,1,2));
        assert(journal.close(ops)==WidgetStep::deferred);
        assert(journal.owns_track(ops,1));
        assert(ops.removed==0 && ops.released==0 && ops.retained==2);
        assert(journal.close(ops)==WidgetStep::deferred);
        assert(ops.unbound==1 && ops.stopped==1);
        ops.drain_result=AnimationQuiescence::complete;
        assert(journal.close(ops)==WidgetStep::ok);
        assert(ops.removed==1 && ops.released==1 && !journal.active_owner());
    }
    std::cout<<"Animation drain ordering, deferred completion, no-retry and reentrancy checks passed\n";
}
