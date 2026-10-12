#pragma once
#include <cstdint>
#include <cstring>
enum class AudioCleanupPhase:uint32_t { None,Context,PrivateReferences,OriginalReferences,ExplicitIdentity,
    OriginalOverlap,CurrentOverlap,Capacity,Acquire,Stop,Destroy,Release,ClosePool,PauseRestore,Complete,SoundFactory };
struct AudioCleanupSnapshot {
    uint32_t magic=0x44413345,version=1,size=64,reserved=0;
    uint32_t phase=0,reason=0,native_error=0,outcome=0,owner_state=0,index=0,step=0;
    uint32_t owned_count=0,original_count=0,original_now_count=0,pause_error=0,pause_native_error=0;
};
static_assert(sizeof(AudioCleanupSnapshot)==64);
class AudioCleanupDiagnostics {
    AudioCleanupSnapshot value_{};
    bool failed_=false;
public:
    void reset() { value_={};failed_=false; }
    void phase(AudioCleanupPhase phase,uint32_t index=0,uint32_t step=0) {
        if(failed_) return;
        value_.phase=static_cast<uint32_t>(phase);value_.index=index;value_.step=step;
        value_.native_error=value_.reason=0;value_.outcome=0;
    }
    void dispatching() { if(!failed_) value_.outcome=2; }
    void returned(uint32_t error,uint32_t outcome) {
        if(failed_) return;value_.native_error=error;value_.outcome=outcome;
    }
    void failure(uint32_t reason=1) { if(!failed_) { value_.reason=reason;failed_=true; } }
    void counts(uint32_t initial,uint32_t now,uint32_t owned) {
        if(failed_) return;
        value_.original_count=initial;value_.original_now_count=now;value_.owned_count=owned;
    }
    void pause(uint32_t error,uint32_t native_error) {
        if(!value_.pause_error || (value_.pause_error==407 && error && error!=407)) { value_.pause_error=error;value_.pause_native_error=native_error; }
    }
    AudioCleanupSnapshot snapshot(uint32_t state) const { auto value=value_;value.owner_state=state;return value; }
};
