#pragma once
#include "audio_pause_journal.h"

// Exact shipping AudioComponent pause state, corroborated by GetPlayState
// 0x3539e10 and SetPaused 0x353bae0. No client-supplied memory offsets.
class OriginalAudioPause {
    AudioPauseJournal<64> journal_;
    MusicAudioReferences refs_{};
    StrongLeasePool<64> leases_;
    uint64_t tokens_[64]{};
    CallPacket pause_{};
    uint64_t base_=0,session_=0;
    bool active_=false;
#ifdef E33_AUDIO_CLEANUP_DIAGNOSTICS_SESSION
    uint32_t diagnostic_error_=0,diagnostic_outcome_=0;
    bool diagnostic_terminal_=false;
#endif
public:
#ifdef E33_AUDIO_CLEANUP_DIAGNOSTICS_SESSION
    uint32_t diagnostic_error() const { return diagnostic_error_; }
    uint32_t diagnostic_outcome() const { return diagnostic_outcome_; }
#endif
    bool active() const { return active_; }
    bool inspect(size_t index,bool& playing,bool& paused) {
        const auto obj=call_identity(base_,refs_.items[index]);
        if(!obj) return false;
        playing=(local_read<uint8_t>(obj+0x8a)&8)!=0;
        paused=(local_read<uint8_t>(obj+0x402)&8)!=0;
        return true;
    }
    AudioPauseResult set(size_t index,bool paused) {
        auto c=pause_; c.target=refs_.items[index]; c.data[0]=paused ? 1 : 0;
#ifdef E33_AUDIO_CLEANUP_DIAGNOSTICS_SESSION
        const bool prior_terminal=diagnostic_terminal_;
        if(!prior_terminal) {
            diagnostic_error_=0;diagnostic_outcome_=2;
            diagnostic_terminal_=true; // Survives SEH before reflected_call returns.
        }
#endif
        const auto error=reflected_call(base_,c);
#ifdef E33_AUDIO_CLEANUP_DIAGNOSTICS_SESSION
        diagnostic_terminal_=prior_terminal;
        if(!diagnostic_terminal_ && (error || c.outcome!=CallDispatchReturned || !diagnostic_error_)) {
            diagnostic_error_=error;diagnostic_outcome_=c.outcome;
            diagnostic_terminal_=c.outcome==2 || (error && error!=201);
        }
#endif
        if(!error && c.outcome==CallDispatchReturned) return AudioPauseResult::Ok;
        if(c.outcome==CallNotDispatched) return error==201 ? AudioPauseResult::Deferred : AudioPauseResult::Rejected;
        return AudioPauseResult::Unknown;
    }
    uint32_t open(uint64_t base,uint64_t session,const CallIdentity& audio,
                  const MusicAudioReferences& refs,const CallPacket& plan) {
        auto c=plan;
        const auto fn=call_identity(base,c.function),pause_target=call_identity(base,c.target);
        if(active_ || !fn || !pause_target || validate_call_packet(c) || c.entry_rva!=0x353bae0 ||
           c.function_flags!=0x4020403 || c.parameter_size!=1 || c.return_offset!=65535 ||
           c.field_count!=1 || c.object_count || c.fields[0].kind!=CallBool || c.fields[0].offset ||
           std::strcmp(c.fields[0].name,"bPause") || c.data[0] ||
           local_read<uint64_t>(fn+0x20)!=audio.address || local_read<uint64_t>(pause_target+0x10)!=audio.address ||
           !(local_read<uint32_t>(pause_target+8)&0x10) || !exact_name(base,fn+0x18,"SetPaused") ||
           reflected_call(base,c,nullptr,nullptr,nullptr,nullptr,true)) return 1512;
        if(leases_.begin(session)!=StrongLeaseResult::Ok || leases_.preflight(session,refs.count)!=StrongLeaseResult::Ok) return 1512;
#ifdef E33_AUDIO_CLEANUP_DIAGNOSTICS_SESSION
        diagnostic_error_=diagnostic_outcome_=0;diagnostic_terminal_=false;
#endif
        base_=base; session_=session; refs_=refs; pause_=plan;
        journal_=AudioPauseJournal<64>{}; active_=true;
        for(unsigned i=0;i<refs_.count;++i) {
            TargetStrongReferenceOps ops{base,refs_.items[i]};
            if(leases_.acquire(ops,session,refs_.items[i].address,tokens_[i])!=StrongLeaseResult::Ok) return 1513;
            refs_.items[i]=call_capture(base,refs_.items[i].address);
        }
        return journal_.open(*this,refs_.count)==AudioPauseResult::Ok ? 0 : 1513;
    }
    uint32_t close() {
#ifdef E33_AUDIO_CLEANUP_DIAGNOSTICS_SESSION
        if(!diagnostic_terminal_) diagnostic_error_=diagnostic_outcome_=0;
#endif
        if(!active_) return 0;
        TargetObjectAssignmentOps context{base_};
        if(!context.context()) return 407;
        const auto outcome=journal_.close(*this);
        if(outcome!=AudioPauseResult::Ok) return outcome==AudioPauseResult::Deferred ? 407 : 1513;
        for(unsigned i=0;i<refs_.count;++i) if(tokens_[i]) {
            TargetStrongReferenceOps ops{base_,refs_.items[i]};
            const auto result=leases_.release(ops,session_,tokens_[i]);
            if(result!=StrongLeaseResult::Ok) return result==StrongLeaseResult::Deferred ? 407 : 1513;
            tokens_[i]=0;
        }
        TargetStrongReferenceOps ops{base_,{}};
        if(leases_.close(ops,session_)!=StrongLeaseResult::Ok) return 1513;
        active_=false; return 0;
    }
};
