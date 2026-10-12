#include "cinematic_widget_journal.h"
#include <cassert>
#include <cstdint>
#include <functional>
#include <iostream>
#include <vector>
using namespace e33_cinematic;
struct Identity {
    uint64_t address=0;
    uint32_t index=0,serial=0;
};
struct Ops {
    unsigned retained=0,released=0;
    std::vector<Identity> detached;
    std::function<void()> on_retain,on_detach,on_release;
    WidgetStep detach_result=WidgetStep::ok,release_result=WidgetStep::ok;
    bool valid(const Identity& id) const { return id.address && id.serial; }
    bool same(const Identity& a,const Identity& b) const {
        return a.address==b.address && a.index==b.index && a.serial==b.serial;
    }
    bool capacity(uint32_t n) const { return retained+n<=32; }
    bool retain(Identity&,uint64_t& token) {
        token=++retained;if(on_retain) on_retain();return true;
    }
    WidgetStep detach(const Identity& id) {
        detached.push_back(id);if(on_detach) on_detach();return detach_result;
    }
    WidgetStep release_all() {
        ++released;if(on_release) on_release();return release_result;
    }
};
int main() {
    const Identity track{0x1000,10,1},widget{0x2000,20,2};
    {
        WidgetJournal<Identity> journal;Ops ops;assert(journal.begin());
        // InputAdded's field is assigned before the getter; journal retains it.
        assert(journal.admit(ops,track,widget));assert(ops.retained==2);
        // InputRemoved may have no remaining root inputs. Known identity still
        // routes privately before Blueprint clears SpawnedUserWidget.
        assert(journal.owns_track(ops,track));
        assert(journal.admit(ops,track,widget));assert(ops.retained==2);
        Identity recycled=track;++recycled.serial;
        assert(!journal.owns_track(ops,recycled));
        // Later evaluation creates a different widget for the same track.
        const Identity replacement{0x3000,30,3};
        assert(journal.admit(ops,track,replacement));assert(ops.retained==4);
        assert(journal.close(ops)==WidgetStep::ok);
        assert(ops.detached.size()==2 && ops.same(ops.detached[0],widget));
        assert(ops.same(ops.detached[1],replacement));assert(ops.released==1);
        assert(!journal.owns_track(ops,track));
    }
    {
        WidgetJournal<Identity> journal;Ops ops;assert(journal.begin());
        // The published record remains recognizable during a nested engine
        // callback, but acquisition or close cannot reenter an uncertain step.
        ops.on_retain=[&] {
            assert(journal.owns_track(ops,track));
            assert(!journal.admit(ops,track,widget));
            assert(journal.close(ops)==WidgetStep::uncertain);
        };
        assert(journal.admit(ops,track,widget));assert(ops.retained==2);
        ops.on_detach=[&] {
            assert(journal.owns_track(ops,track));
            assert(!journal.admit(ops,track,widget));
            assert(journal.close(ops)==WidgetStep::uncertain);
        };
        ops.on_release=[&] { assert(journal.close(ops)==WidgetStep::uncertain); };
        assert(journal.close(ops)==WidgetStep::ok);
        assert(ops.detached.size()==1 && ops.released==1);
    }
    {
        WidgetJournal<Identity> journal;Ops ops;assert(journal.begin());
        for(unsigned n=0;n<16;++n) {
            Identity t{0x1000+uint64_t(n)*256,100+n,1};
            Identity w{0x10000+uint64_t(n)*256,200+n,2};
            assert(journal.admit(ops,t,w));
        }
        assert(ops.retained==32 && journal.count()==16);
        assert(!journal.admit(ops,track,widget));assert(ops.retained==32);
        assert(journal.close(ops)==WidgetStep::ok);
        assert(ops.detached.size()==16 && ops.released==1);
    }
    std::cout<<"Widget callback lifecycle, stable identities, bounds and reentrancy checks passed\n";
}
