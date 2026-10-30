#include "cinematic_widget_journal.h"
#include <cassert>
#include <vector>
#include <iostream>
using namespace e33_cinematic;
struct Ops {
    int retained=0,detached=0,released=0,fail_retain=0;
    bool room=true,alive=true;
    WidgetStep detach_result=WidgetStep::ok, release_result=WidgetStep::ok;
    bool valid(uint64_t id) const { return id && alive; }
    bool same(uint64_t a,uint64_t b) const { return a==b; }
    bool capacity(uint32_t) const { return room; }
    bool retain(uint64_t&,uint64_t& token) { ++retained; token=uint64_t(retained);return retained!=fail_retain; }
    WidgetStep detach(uint64_t) { ++detached;return detach_result; }
    WidgetStep release_all() { ++released;return release_result; }
};
int main() {
    {
        WidgetJournal<uint64_t> j;Ops ops;assert(j.begin());assert(j.admit(ops,1,2));
        // Positive world retirement bypasses all old-widget detach callbacks.
        ops.alive=false;ops.release_result=WidgetStep::deferred;
        assert(j.retire(ops)==WidgetStep::deferred);assert(ops.detached==0 && j.active_owner());
        ops.release_result=WidgetStep::ok;assert(j.retire(ops)==WidgetStep::ok);
        assert(ops.detached==0 && !j.active_owner());assert(j.retire(ops)==WidgetStep::ok);
        assert(ops.released==2);
    }
    {
        WidgetJournal<uint64_t> j;Ops ops;assert(j.begin());ops.fail_retain=2;
        assert(!j.admit(ops,1,2));assert(!j.retirement_ready());
        assert(j.retire(ops)==WidgetStep::uncertain);assert(ops.detached==0 && ops.released==0);
    }
    {
        WidgetJournal<uint64_t> j;Ops ops;assert(j.begin());assert(j.admit(ops,1,2));
        ops.release_result=WidgetStep::uncertain;assert(j.retire(ops)==WidgetStep::uncertain);
        ops.release_result=WidgetStep::ok;assert(j.retire(ops)==WidgetStep::uncertain);
        assert(ops.released==1 && ops.detached==0);
    }
    {
        WidgetJournal<uint64_t,2> j; Ops ops;
        assert(j.begin());assert(!j.begin());assert(j.admit(ops,1,2));
        assert(j.admit(ops,1,2));assert(ops.retained==2);assert(j.owns_track(ops,1));
        assert(j.admit(ops,1,3));assert(j.count()==2);assert(!j.admit(ops,4,5));
        // Known track remains owned independently of an engine input array.
        assert(j.owns_track(ops,1));assert(!j.owns_track(ops,4));
        assert(j.close(ops)==WidgetStep::ok);assert(ops.detached==2);assert(ops.released==1);
        assert(!j.active_owner());assert(j.close(ops)==WidgetStep::ok);assert(ops.released==1);
    }
    {
        WidgetJournal<uint64_t> j;Ops ops;assert(j.begin());ops.room=false;
        assert(!j.admit(ops,1,2));assert(ops.retained==0);assert(!j.quarantined());
        ops.room=true;ops.fail_retain=2;assert(!j.admit(ops,1,2));assert(j.quarantined());
        assert(j.owns_track(ops,1)); // Quarantine must not turn InputRemoved into an unrelated call.
        assert(j.close(ops)==WidgetStep::uncertain);assert(ops.detached==0 && ops.released==0);
    }
    {
        WidgetJournal<uint64_t> j;Ops ops;assert(j.begin());assert(j.admit(ops,1,2));
        ops.detach_result=WidgetStep::deferred;assert(j.close(ops)==WidgetStep::deferred);
        assert(ops.released==0);ops.detach_result=WidgetStep::ok;
        ops.release_result=WidgetStep::deferred;assert(j.close(ops)==WidgetStep::deferred);
        assert(ops.detached==2);ops.release_result=WidgetStep::ok;
        assert(j.close(ops)==WidgetStep::ok);assert(ops.detached==2 && ops.released==2);
    }
    {
        WidgetJournal<uint64_t> j;Ops ops;assert(j.begin());assert(j.admit(ops,1,2));
        ops.detach_result=WidgetStep::uncertain;assert(j.close(ops)==WidgetStep::uncertain);
        assert(j.owns_track(ops,1));
        ops.detach_result=WidgetStep::ok;assert(j.close(ops)==WidgetStep::uncertain);
        assert(ops.detached==1 && ops.released==0);
    }
    {
        WidgetJournal<uint64_t> j;Ops ops;assert(j.begin());assert(j.admit(ops,1,2));
        ops.alive=false;assert(!j.owns_track(ops,1));assert(j.close(ops)==WidgetStep::ok);
        assert(ops.detached==0 && ops.released==1);
    }
    std::cout<<"Cinematic widget ownership journal checks passed\n";
}
