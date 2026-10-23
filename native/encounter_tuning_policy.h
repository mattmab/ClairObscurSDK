#pragma once
#include <cmath>
#include <cstdint>
#include <algorithm>

namespace e33_encounter_tuning {
struct Settings {
    uint32_t level_mode=0; // 0 authored, 1 offset, 2 override
    int32_t level=0,difficulty=-1; // -1 retains game difficulty
    double health=1.;
    bool valid()const {
        return level_mode<=2 && (level_mode==0?level==0:level_mode==1?(level>=-98&&level<=98):(level>=1&&level<=99)) &&
            difficulty>=-1&&difficulty<=2&&std::isfinite(health)&&health>=.1&&health<=1000.;
    }
    bool defaults()const{return level_mode==0&&difficulty==-1&&health==1.;}
};
// Empty combat rosters also occur between abandon and retry. Restore the
// current manager's scalars there, but retain this owned encounter's hooks
// until explicit retirement. A subsequent original spawn reapplies settings.
class RetryLifetime {
    bool seen_=false,idle_=false,closed_=false;
public:
    bool accepts_call()const{return !closed_;}
    bool battle_observed()const{return seen_;}
    bool restored()const{return idle_||closed_;}
    void observe_owned_call(){if(!closed_){seen_=true;idle_=false;}}
    bool observe_idle(){
        if(closed_||!seen_||idle_)return false;
        idle_=true;return true;
    }
    void close(){closed_=true;}
};
// Compare-before-restore: never overwrite a value changed by another system.
// Repeated spawn/getter calls reuse the baseline, rather than compounding.
template<class T> struct ScalarOverride {
    bool applied=false;T before{},written{};
    T baseline(T current){if(!applied||current!=written)before=current;return before;}
    void set(T& current,T value){baseline(current);written=value;applied=true;current=value;}
    void restore(T& current){if(applied&&current==written)current=before;applied=false;}
};
inline int32_t level_for(const Settings& s,int32_t authored){
    return s.level_mode==2?s.level:s.level_mode==1?std::clamp(authored+s.level,1,99):authored;
}
}
