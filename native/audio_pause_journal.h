#pragma once
#include <cstddef>
#include <cstdint>

enum class AudioPauseResult { Ok, Deferred, Rejected, Unknown };

// Operations run on the game thread. Identity retention belongs to the adapter.
// Never replay an uncertain setter; known completed entries can still restore.
template<size_t Capacity> class AudioPauseJournal {
    enum Stage : uint8_t { Unchanged, Pending, Paused, Uncertain, Restored };
    Stage stages_[Capacity]{};
    size_t count_=0;
    bool started_=false;
public:
    bool active() const {
        for(size_t i=0;i<count_;++i) if(stages_[i]==Paused || stages_[i]==Uncertain) return true;
        return false;
    }
    template<class Ops> AudioPauseResult open(Ops& ops,size_t count) {
        if(started_ || count>Capacity) return AudioPauseResult::Rejected;
        started_=true; count_=count;
        // Inspect every retained component before changing any one of them.
        for(size_t i=0;i<count_;++i) {
            bool playing=false,paused=false;
            if(!ops.inspect(i,playing,paused)) return AudioPauseResult::Rejected;
            stages_[i]=playing && !paused ? Pending : Unchanged;
        }
        for(size_t i=0;i<count_;++i) if(stages_[i]==Pending) {
            stages_[i]=Uncertain;
            const auto result=ops.set(i,true);
            if(result==AudioPauseResult::Ok) stages_[i]=Paused;
            else {
                if(result==AudioPauseResult::Deferred || result==AudioPauseResult::Rejected) stages_[i]=Unchanged;
                return result;
            }
        }
        return AudioPauseResult::Ok;
    }
    AudioPauseResult abandon_retired_world() {
        // Validate all entries first; never partially erase an unknown setter.
        for(size_t i=0;i<count_;++i)if(stages_[i]==Uncertain)return AudioPauseResult::Unknown;
        for(size_t i=0;i<count_;++i)stages_[i]=Restored;
        return AudioPauseResult::Ok;
    }
    template<class Ops> AudioPauseResult close(Ops& ops) {
        bool unknown=false,deferred=false;
        for(size_t i=0;i<count_;++i) {
            if(stages_[i]==Uncertain) { unknown=true; continue; }
            if(stages_[i]!=Paused) continue;
            bool playing=false,paused=false;
            if(!ops.inspect(i,playing,paused)) { stages_[i]=Uncertain; unknown=true; continue; }
            if(!paused) { stages_[i]=Restored; continue; }
            stages_[i]=Uncertain;
            const auto result=ops.set(i,false);
            if(result==AudioPauseResult::Ok) stages_[i]=Restored;
            else if(result==AudioPauseResult::Deferred || result==AudioPauseResult::Rejected) {
                stages_[i]=Paused; deferred=true;
            } else unknown=true;
        }
        return unknown ? AudioPauseResult::Unknown : deferred ? AudioPauseResult::Deferred : AudioPauseResult::Ok;
    }
};
