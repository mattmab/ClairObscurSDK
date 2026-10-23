#pragma once
#include <algorithm>
#include <cmath>
namespace e33_runtime_cinematic {
// One fixed demonstration, not a general timeline or asset-authoring system.
struct Timing {
    bool animation=false,audio=false;
    unsigned audio_count=0;
    inline static constexpr double audio_times[]={2.5,4.2,5.8666667,8.,9.2333333,12.6,14.2,15.9666667,19.3333333};
    bool animation_due(double seconds) const {return !animation && seconds>=1. && seconds<20.;}
    bool audio_due(double seconds) const {return audio_count<9 && seconds>=audio_times[audio_count] && seconds<20.;}
    void audio_fired(){audio=true;++audio_count;}
    static bool finished(double seconds) {return !std::isfinite(seconds) || seconds>=20.;}
    static double movement(double seconds) {return std::clamp((seconds-2.)/16.,0.,1.);}
};
}
