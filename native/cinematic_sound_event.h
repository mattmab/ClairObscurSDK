#pragma once
#include "cinematic_sound_event_protocol.h"
#include "cinematic_sound_diagnostics.h"

// Exact Prologue title adapter. This replaces only the audited, no-argument
// sound event for this SDK-owned sequence player. It is not a Blueprint call
// API and does not broaden the observation-only damage trace profile.
class CinematicSoundEvent {
    inline static uint64_t base_=0;
    inline static CinematicSoundEvent* current_=nullptr;
    uint64_t owner_=0,function_token_=0;
    CallIdentity function_{},player_{},sound_{},director_class_{};
    CallPacket play_{};
#ifdef E33_EMPTY_TITLE_SESSION
    bool empty_trap_=false;
    static bool trap_armed(const CallIdentity& player) {
        return current_ && current_->empty_trap_ && current_->state_==1 &&
            !std::memcmp(&current_->player_,&player,sizeof(player));
    }
    static bool trap_profile(uint64_t base,const CallIdentity& function,CallIdentity& cls_id) {
        const auto fn=call_identity(base,function);
        if(!fn || local_read<uint32_t>(fn+0xb0)!=0x0c000000 ||
           local_read<uint16_t>(fn+0xb6) || local_read<uint16_t>(fn+0xb8)!=65535 ||
           local_read<uint64_t>(fn+0xd8)!=base+0x13937a0 ||
           !exact_name(base,fn+24,"SequenceEvent")) return false;
        const auto cls=local_read<uint64_t>(fn+32);
        if(!e33_empty_title::named(base,cls,"LS_Title_BackAtCamp_DirectorBP_C",
              "/Game/Cinematics/Titles/SequenceTitles/LS_Title_BackAtCamp")) return false;
        const auto director=local_read<uint64_t>(cls+64);
        if(!e33_empty_title::named(base,director,"LevelSequenceDirector","/Script/LevelSequence") ||
           !music_field(base,director,"Player",56,8,0x6e11d38,0x11c001000000214ULL)) return false;
        const auto script=local_read<uint64_t>(fn+0x60);
        if(!script || local_read<int32_t>(fn+0x68)!=18) return false;
        const auto uber=local_read<uint64_t>(script+1);
        if(!call_capture(base,uber).address || local_read<uint64_t>(uber+32)!=cls ||
           !exact_name(base,uber+24,"ExecuteUbergraph_LS_Title_BackAtCamp_DirectorBP") ||
           local_read<uint32_t>(uber+0xb0)!=0x8001 || local_read<uint64_t>(uber+0xd8)!=base+0x13937a0 ||
           local_read<int32_t>(uber+0x68)!=132) return false;
        const uint8_t event[]={0x46,0,0,0,0,0,0,0,0,0x1d,0x0a,0,0,0,0x16,4,0x0b,0x53};
        const uint32_t offsets[]={1};const uint64_t values[]={uber};
        if(!bytes(fn,event,sizeof(event),offsets,values,1)) return false;
        cls_id=call_capture(base,cls);return cls_id.address!=0;
    }
#endif
    uint32_t state_=0,observed_=0,failed_=0;
#ifdef E33_SOUND_EVENT_DIAGNOSTICS_SESSION
    e33_cinematic::SoundEventDiagnostics diagnostics_{};
#endif
    static bool bytes(uint64_t fn,const uint8_t* expected,size_t size,
                      const uint32_t* pointers,const uint64_t* values,size_t count) {
        const auto data=local_read<uint64_t>(fn+0x60);
        const auto length=local_read<int32_t>(fn+0x68),capacity=local_read<int32_t>(fn+0x6c);
        if(!data || length!=static_cast<int32_t>(size) || capacity<length || capacity>65536) return false;
        for(size_t i=0;i<size;++i) {
            bool pointer=false;
            for(size_t j=0;j<count;++j) if(i>=pointers[j] && i<pointers[j]+8) pointer=true;
            if(!pointer && local_read<uint8_t>(data+i)!=expected[i]) return false;
        }
        for(size_t j=0;j<count;++j) if(local_read<uint64_t>(data+pointers[j])!=values[j]) return false;
        return true;
    }
    static bool profile(uint64_t base,const CallIdentity& function,const CallIdentity& sound,CallIdentity& cls_id) {
        const auto fn=call_identity(base,function), audio=call_identity(base,sound);
        if(!fn || !audio || local_read<uint32_t>(fn+0xb0)!=0x0c000000 ||
           local_read<uint16_t>(fn+0xb6) || local_read<uint16_t>(fn+0xb8)!=65535 ||
           local_read<uint64_t>(fn+0xd8)!=base+0x13937a0 || !exact_name(base,fn+0x18,"SequenceEvent")) return false;
        const auto cls=local_read<uint64_t>(fn+0x20), package=local_read<uint64_t>(cls+0x20);
        if(!exact_name(base,cls+0x18,"LS_Title_PrologueLumiere_DirectorBP_C") ||
           !exact_name(base,package+0x18,
                       "/Game/Cinematics/Titles/SequenceTitles/LS_Title_PrologueLumiere") ||
           !exact_name(base,audio+0x18,"Exp33_TitleCards_01_Prologue_Lumiere") ||
           !exact_name(base,local_read<uint64_t>(audio+0x20)+0x18,
                       "/Game/Audio/WAV/MUSIC/TitlesCards/Exp33_TitleCards_01_Prologue_Lumiere")) return false;
        const auto director=local_read<uint64_t>(cls+0x40);
        if(!exact_name(base,director+0x18,"LevelSequenceDirector") ||
           !exact_name(base,local_read<uint64_t>(director+0x20)+0x18,"/Script/LevelSequence") ||
           !music_field(base,director,"Player",56,8,0x6e11d38,0x11c001000000214ULL)) return false;
        const auto script=local_read<uint64_t>(fn+0x60);
        if(!script || local_read<int32_t>(fn+0x68)!=18) return false;
        const auto uber=local_read<uint64_t>(script+1);
        if(!call_capture(base,uber).address || local_read<uint64_t>(uber+0x20)!=cls ||
           !exact_name(base,uber+0x18,"ExecuteUbergraph_LS_Title_PrologueLumiere_DirectorBP") ||
           local_read<uint32_t>(uber+0xb0)!=0x8001 || local_read<uint16_t>(uber+0xb6)!=4 ||
           local_read<uint64_t>(uber+0xd8)!=base+0x13937a0) return false;
        const uint8_t event[]={0x46,0,0,0,0,0,0,0,0,0x1d,0x4b,0,0,0,0x16,4,0x0b,0x53};
        const uint32_t event_offsets[]={1}; const uint64_t event_values[]={uber};
        if(!bytes(fn,event,sizeof(event),event_offsets,event_values,1)) return false;
        const auto graph=local_read<uint64_t>(uber+0x60);
        if(!graph || local_read<int32_t>(uber+0x68)!=83) return false;
        const auto entry=local_read<uint64_t>(graph+2), defaults=local_read<uint64_t>(graph+12), play=local_read<uint64_t>(graph+33);
        if(entry!=local_read<uint64_t>(uber+0x50) ||
           !music_field(base,uber,"EntryPoint",0,4,0x6e10a98,0x8001040000294ULL) ||
           !call_capture(base,defaults).address || !call_capture(base,play).address ||
           !exact_name(base,defaults+0x18,"Default__GameplayStatics") ||
           !exact_name(base,play+0x18,"PlaySound2D") || local_read<uint64_t>(play+0xd8)!=base+0x373e3b0 ||
           local_read<uint64_t>(defaults+0x10)!=local_read<uint64_t>(play+0x20)) return false;
        const uint8_t graph_bytes[]={
            0x4e,0,0,0,0,0,0,0,0,0,0x19,0x20,0,0,0,0,0,0,0,0,0x26,0,0,0,0,0,0,0,0,0,0,0,
            0x1c,0,0,0,0,0,0,0,0,0x17,0x20,0,0,0,0,0,0,0,0,0x1e,0,0,0x80,0x3f,
            0x1e,0,0,0x80,0x3f,0x1e,0,0,0,0,0x2a,0x2a,0x27,0x16,6,0x50,0,0,0,6,0x0a,0,0,0,4,0x0b,0x53};
        static_assert(sizeof(graph_bytes)==83);
        const uint32_t graph_offsets[]={2,12,33,43}; const uint64_t graph_values[]={entry,defaults,play,audio};
        if(!bytes(uber,graph_bytes,sizeof(graph_bytes),graph_offsets,graph_values,4)) return false;
        cls_id=call_capture(base,cls); return cls_id.address!=0;
    }
    static bool selected(void* object,void* frame,CinematicSoundEvent*& diagnostic_owner) {
        if(GetCurrentThreadId()!=local_read<DWORD>(base_+0x9272d30)) return false;
        auto* self=current_;
        if(!self || !self->state_) return false;
        diagnostic_owner=self;
#ifdef E33_SOUND_EVENT_DIAGNOSTICS_SESSION
        e33_cinematic::sound_count(self->diagnostics_.eligible_game_thread_calls);
#endif
        const auto obj=reinterpret_cast<uint64_t>(object);
        if(!obj || !frame || !call_identity(base_,self->function_) || !call_identity(base_,self->director_class_) ||
           local_read<uint64_t>(reinterpret_cast<uint64_t>(frame)+0x10)!=self->function_.address) return false;
#ifdef E33_SOUND_EVENT_DIAGNOSTICS_SESSION
        e33_cinematic::sound_count(self->diagnostics_.exact_function_frames);
#endif
        if(local_read<uint64_t>(obj+0x10)!=self->director_class_.address) return false;
#ifdef E33_SOUND_EVENT_DIAGNOSTICS_SESSION
        e33_cinematic::sound_count(self->diagnostics_.exact_directors);
#endif
        if(!call_identity(base_,self->player_) || local_read<uint64_t>(obj+56)!=self->player_.address) return false;
#ifdef E33_SOUND_EVENT_DIAGNOSTICS_SESSION
        e33_cinematic::sound_count(self->diagnostics_.player_matches);
#endif
        return true;
    }
    static void __fastcall route(void* object,void* frame,void* result) {
        bool ours=false;CinematicSoundEvent* diagnostic_owner=nullptr;
        __try { ours=selected(object,frame,diagnostic_owner); }
        __except(EXCEPTION_EXECUTE_HANDLER) {
#ifdef E33_SOUND_EVENT_DIAGNOSTICS_SESSION
            if(diagnostic_owner) e33_cinematic::sound_count(diagnostic_owner->diagnostics_.failures);
#endif
            ours=false;
        }
        if(!ours) {
            reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(base_+0x13937a0)(object,frame,result); return;
        }
        auto* self=current_;
        if(self->state_==2) return; // Prior uncertain dispatch: suppress, never retry.
        ++self->observed_;
#ifdef E33_SOUND_EVENT_DIAGNOSTICS_SESSION
        e33_cinematic::sound_count(self->diagnostics_.selected_dispatches);
#endif
#ifdef E33_EMPTY_TITLE_SESSION
        if(self->empty_trap_) {
            ++self->failed_; self->state_=2;
#ifdef E33_SOUND_EVENT_DIAGNOSTICS_SESSION
            e33_cinematic::sound_count(self->diagnostics_.failures);
#endif
            return; // Unexpected event: suppress, report failure, allow owned cleanup.
        }
#endif
        // No fall-through after dispatch: an uncertain native call must never
        // also execute the original_entry fire-and-forget sound event.
        __try {
            auto call=self->play_;
            if(reflected_call(base_,call) || call.outcome!=CallDispatchReturned) {
#ifdef E33_SOUND_EVENT_DIAGNOSTICS_SESSION
                e33_cinematic::sound_count(self->diagnostics_.failures);
#endif
                ++self->failed_; self->state_=2;
            }
        } __except(EXCEPTION_EXECUTE_HANDLER) {
#ifdef E33_SOUND_EVENT_DIAGNOSTICS_SESSION
            e33_cinematic::sound_count(self->diagnostics_.failures);
#endif
            ++self->failed_; self->state_=2;
        }
    }
public:
    bool active() const { return state_!=0; }
    bool protects(uint64_t token) const { return active() && token==function_token_; }
    uint32_t close(uint64_t base) {
        if(!active()) return 0;
        TargetObjectAssignmentOps context{base};
        if(!context.context()) return 407;
        if(!call_identity(base,function_)) { state_=2; return 1503; }
        auto slot=reinterpret_cast<void* volatile*>(function_.address+0xd8);
        auto original_entry=reinterpret_cast<void*>(base+0x13937a0);
        const auto previous=InterlockedCompareExchangePointer(slot,original_entry,reinterpret_cast<void*>(&route));
        if(previous!=original_entry && previous!=reinterpret_cast<void*>(&route)) { state_=2; return 1503; }
        state_=0; current_=nullptr; return 0;
    }
    template<class Pool,class Sequence,class Audio>
    void command(uint64_t base,uint64_t session,Pool& leases,Sequence& sequence,Audio& audio,CinematicSoundEventPacket& p) {
        const uint32_t maximum_operation=
#ifdef E33_SOUND_EVENT_DIAGNOSTICS_SESSION
            4;
#else
            3;
#endif
        const bool trap=
#ifdef E33_EMPTY_TITLE_SESSION
            p.version==2;
#else
            false;
#endif
        if((p.version!=1 && !trap) || !p.owner || p.reserved || p.error || p.state || p.observed || p.failed || p.operation<1 || p.operation>maximum_operation) { p.error=1500; return; }
        if(p.operation!=1) {
            const auto payload=reinterpret_cast<const uint8_t*>(&p.function);
            for(size_t i=0;i<sizeof(p)-40;++i) if(payload[i]) { p.error=1501; return; }
            if(p.owner!=owner_
#ifdef E33_EMPTY_TITLE_SESSION
               || trap!=empty_trap_
#endif
            ) { p.error=1501; return; }
            if(p.operation==2) p.error=close(base);
#ifdef E33_SOUND_EVENT_DIAGNOSTICS_SESSION
            if(p.operation==4) {
                if(!active()) { p.error=1501;return; }
                e33_cinematic::sound_diagnostics_payload(&p.function,sizeof(p)-40,diagnostics_);
            }
#endif
        } else {
            auto call=p.play;
            CallIdentity cls{};
#ifdef E33_EMPTY_TITLE_SESSION
            if(trap) {
                const auto payload=reinterpret_cast<const uint8_t*>(&p.sound);
                for(size_t i=0;i<sizeof(p.sound);++i) if(payload[i]) { p.error=1502;return; }
                const auto call_bytes=reinterpret_cast<const uint8_t*>(&p.play);
                for(size_t i=0;i<sizeof(p.play);++i) if(call_bytes[i]) { p.error=1502;return; }
                if(active() || !sequence.owns_empty_title_player(p.player) ||
                   !leases.owns_object(session,p.function_token,p.function.address) ||
                   !trap_profile(base,p.function,cls)) { p.error=1502;return; }
            } else
#endif
            if(active() || !sequence.owns_player(p.player) || !audio.owns_component(call.target,p.sound) ||
               !leases.owns_object(session,p.function_token,p.function.address) || !profile(base,p.function,p.sound,cls) ||
               validate_call_packet(call) || call.entry_rva!=0x353a330 || call.parameter_size!=4 || call.return_offset!=65535 ||
               call.field_count!=1 || call.object_count || call.fields[0].kind!=CallFloat ||
               std::strcmp(call.fields[0].name,"StartTime") || call.fields[0].offset ||
               local_read<uint32_t>(reinterpret_cast<uint64_t>(call.data)) ||
               !exact_name(base,call.function.address+0x18,"Play") || reflected_call(base,call,nullptr,nullptr,nullptr,nullptr,true)) { p.error=1502; return; }
            HMODULE pinned{};
            if((base_ && base_!=base) || !GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
                    reinterpret_cast<LPCWSTR>(&route),&pinned)) { p.error=1502; return; }
#ifdef E33_EMPTY_TITLE_SESSION
            empty_trap_=trap; cinematic_empty_trap_armed=&trap_armed;
#endif
            base_=base; owner_=p.owner; function_token_=p.function_token;
            function_=p.function; player_=p.player; sound_=p.sound; director_class_=cls; play_=p.play;
            observed_=failed_=0; current_=this;
#ifdef E33_SOUND_EVENT_DIAGNOSTICS_SESSION
            diagnostics_={};
#endif
            auto slot=reinterpret_cast<void* volatile*>(function_.address+0xd8);
            auto original_entry=reinterpret_cast<void*>(base+0x13937a0);
            state_=1;
            if(InterlockedCompareExchangePointer(slot,reinterpret_cast<void*>(&route),original_entry)!=original_entry) {
                state_=0; current_=nullptr; p.error=1502;
            }
        }
        p.state=state_; p.observed=observed_; p.failed=failed_;
    }
};
