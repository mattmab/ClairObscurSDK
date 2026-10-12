#include "audio_pause_journal.h"
#include <cassert>
#include <cstdio>
struct Ops {
    bool playing[3]{true,true,false},paused[3]{false,true,false};
    int calls[3]{};
    int fail=-1;
    AudioPauseResult failure=AudioPauseResult::Unknown;
    bool inspect(size_t i,bool& p,bool& s) { p=playing[i]; s=paused[i]; return true; }
    AudioPauseResult set(size_t i,bool state) {
        ++calls[i];
        if(static_cast<int>(i)==fail) return failure;
        paused[i]=state; return AudioPauseResult::Ok;
    }
};
int main() {
    {
        Ops ops; AudioPauseJournal<3> journal;
        assert(journal.open(ops,3)==AudioPauseResult::Ok);
        assert(ops.paused[0] && ops.paused[1] && !ops.paused[2]);
        assert(journal.close(ops)==AudioPauseResult::Ok);
        assert(!ops.paused[0] && ops.paused[1] && !ops.paused[2]);
        assert(ops.calls[0]==2 && !ops.calls[1] && !ops.calls[2]);
        assert(journal.close(ops)==AudioPauseResult::Ok && ops.calls[0]==2);
    }
    {
        Ops ops; ops.paused[1]=false; ops.fail=1;
        AudioPauseJournal<3> journal;
        assert(journal.open(ops,3)==AudioPauseResult::Unknown);
        assert(journal.close(ops)==AudioPauseResult::Unknown);
        assert(!ops.paused[0] && ops.calls[0]==2 && ops.calls[1]==1);
        assert(journal.close(ops)==AudioPauseResult::Unknown && ops.calls[1]==1);
    }
    {
        Ops ops; AudioPauseJournal<3> journal;
        assert(journal.open(ops,3)==AudioPauseResult::Ok);
        ops.fail=0; ops.failure=AudioPauseResult::Deferred;
        assert(journal.close(ops)==AudioPauseResult::Deferred && journal.active());
        ops.fail=-1;
        assert(journal.close(ops)==AudioPauseResult::Ok && !journal.active());
    }
    std::puts("Audio pause restoration: pre-paused/stopped preservation, partial failure, no uncertain retry, deferred cleanup passed");
}
