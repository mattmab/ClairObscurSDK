#pragma once
#include <cstdint>

namespace e33_enemy_spawn {
enum class HelperEntryPhase { Empty, AwaitingActive, ActiveSeen, Retired };
// Actor lifetime is independent of the input frame's engine-copy handoff.
// Unknown startup never expires into cleanup eligibility.
class HelperEntryLifetime {
    HelperEntryPhase phase_=HelperEntryPhase::Empty;
    uint64_t name_=0;
public:
    HelperEntryPhase phase()const{return phase_;}
    uint64_t name()const{return name_;}
    bool pending()const{return phase_==HelperEntryPhase::AwaitingActive||phase_==HelperEntryPhase::ActiveSeen;}
    bool ready()const{return phase_==HelperEntryPhase::Empty||phase_==HelperEntryPhase::Retired;}
    bool begin(uint64_t name){
        if(phase_!=HelperEntryPhase::Empty||!name)return false;
        name_=name;phase_=HelperEntryPhase::AwaitingActive;return true;
    }
    void observe(bool own_active,bool proven_idle){
        if(own_active){
            if(phase_==HelperEntryPhase::AwaitingActive)phase_=HelperEntryPhase::ActiveSeen;
            return; // contradictory input cannot prove retirement
        }
        if(proven_idle&&phase_==HelperEntryPhase::ActiveSeen)phase_=HelperEntryPhase::Retired;
    }
};
}
