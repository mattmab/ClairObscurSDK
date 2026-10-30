#include "audio_pause_journal.h"
#include <cassert>
#include <cstdio>
struct Ops {
    bool paused[2]{},playing[2]{true,true};
    unsigned calls[2]{};bool foreign[2]{};
    AudioPauseCertificate certificate_value=AudioPauseCertificate::Current;
    AudioPauseResult outcome=AudioPauseResult::Ok;
    bool inspect(size_t i,bool&playing_out,bool&paused_out){playing_out=playing[i];paused_out=paused[i];return true;}
    AudioPauseResult set(size_t i,bool value){++calls[i];if(outcome==AudioPauseResult::Ok)paused[i]=value;return outcome;}
    AudioPauseCertificate certificate(size_t i){return foreign[i]?AudioPauseCertificate::Foreign:certificate_value;}
};
int main(){
    {Ops ops;AudioPauseJournal<2> journal;assert(journal.open(ops,2)==AudioPauseResult::Ok);
     ops.foreign[0]=true;assert(journal.retire_world(ops)==AudioPauseResult::Ok);
     assert(ops.paused[0]&&!ops.paused[1]&&ops.calls[0]==1&&ops.calls[1]==2);}
    {Ops ops;AudioPauseJournal<2> journal;assert(journal.open(ops,2)==AudioPauseResult::Ok);
     ops.certificate_value=AudioPauseCertificate::Pending;assert(journal.retire_world(ops)==AudioPauseResult::Deferred);
     assert(ops.calls[0]==1&&ops.calls[1]==1);ops.certificate_value=AudioPauseCertificate::Current;
     assert(journal.retire_world(ops)==AudioPauseResult::Ok);}
    {Ops ops;AudioPauseJournal<2> journal;assert(journal.open(ops,2)==AudioPauseResult::Ok);
     ops.outcome=AudioPauseResult::Unknown;assert(journal.retire_world(ops)==AudioPauseResult::Unknown);
     const auto calls=ops.calls[0];ops.outcome=AudioPauseResult::Ok;
     assert(journal.retire_world(ops)==AudioPauseResult::Unknown&&ops.calls[0]==calls);}
    {Ops ops;AudioPauseJournal<2> journal;assert(journal.open(ops,2)==AudioPauseResult::Ok);
     ops.paused[0]=false;ops.foreign[1]=true;assert(journal.retire_world(ops)==AudioPauseResult::Ok);
     assert(ops.calls[0]==1&&ops.calls[1]==1);}
    {Ops ops;AudioPauseJournal<2> journal;assert(journal.open(ops,2)==AudioPauseResult::Ok);
     ops.outcome=AudioPauseResult::Deferred;assert(journal.retire_world(ops)==AudioPauseResult::Deferred);
     ops.outcome=AudioPauseResult::Ok;assert(journal.retire_world(ops)==AudioPauseResult::Ok);}
    std::puts("Audio retired-world pause certificates passed");
}
