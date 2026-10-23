#include "runtime_cinematic_timing.h"
#include <cassert>
#include <limits>
int main(){
    using e33_runtime_cinematic::Timing;
    Timing t;
    assert(!t.animation_due(0.999));assert(t.animation_due(1.));
    t.animation=true;assert(!t.animation_due(1.001));
    for(unsigned i=0;i<9;++i){
        const auto at=Timing::audio_times[i];
        assert(!t.audio_due(at-.001));assert(t.audio_due(at));
        t.audio_fired();assert(t.audio_count==i+1);assert(!t.audio_due(at+.001));
    }
    assert(t.audio);assert(!t.audio_due(19.999));
    assert(Timing::movement(-1.)==0.);assert(Timing::movement(2.)==0.);
    assert(Timing::movement(10.)==.5);assert(Timing::movement(18.)==1.);
    assert(Timing::movement(20.)==1.);assert(!Timing::finished(19.999));
    assert(Timing::finished(20.));assert(Timing::finished(std::numeric_limits<double>::quiet_NaN()));
    Timing late;assert(!late.animation_due(20.));assert(!late.audio_due(20.));
    return 0;
}
