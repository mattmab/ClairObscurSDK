#pragma once
#include "cinematic_widget_protocol.h"
#include "cinematic_widget_owner.h"
#include "cinematic_callback_profile.h"
#include "cinematic_component_frame.h"
#include "cinematic_widget_diagnostics.h"

// One exact getter callsite, one retained SDK sequence. No public arbitrary
// return substitution, memory writes or broad Blueprint trace admission.
class CinematicWidgetHook {
    inline static uint64_t base_=0;
    inline static CinematicWidgetHook* current_=nullptr;
    uint64_t owner_=0,script_=0,return_property_=0,tokens_[WidgetResourceCount]{};
    CallIdentity resources_[WidgetResourceCount]{},player_{};
    CinematicWidgetOwner widgets_;
    uint32_t state_=0,observed_=0,failed_=0;
    e33_cinematic::WidgetDiagnostics diagnostics_{};

    bool frame(void* actor,void* stack,void* result,e33_cinematic::ComponentLookupFrame& out) const {
        TargetObjectAssignmentOps context{base_};
        if(!context.context()) return false;
        ULONG_PTR low{},high{};GetCurrentThreadStackLimits(&low,&high);
        e33_cinematic::ComponentLookupSite site{resources_[WidgetGetter].address,
            resources_[WidgetNativeGetter].address,script_,resources_[WidgetLibrary].address,
            reinterpret_cast<uint64_t>(actor),low,high,return_property_};
        auto read=[](uint64_t address,void* output,size_t size) {
            std::memcpy(output,reinterpret_cast<const void*>(address),size);return true;};
        return e33_cinematic::component_lookup_frame(read,reinterpret_cast<uint64_t>(stack),
            reinterpret_cast<uint64_t>(result),site,out,true);
    }
    static void __fastcall route(void* actor,void* stack,void* result) {
        // Preserve argument stepping and VM bookkeeping of the real wrapper.
        // Its ordinary engine result is changed only after a bounded, exact
        // call-frame and owned-root match; unrelated calls are untouched.
        reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(base_+0x333a230)(actor,stack,result);
        // Diagnostics and mutable ownership state are game-thread-only. Other
        // callers retain the original engine result without touching counters.
        TargetObjectAssignmentOps context{base_};
        if(!context.context()) return;
        auto* self=current_;
        if(!self || !self->state_) return;
        e33_cinematic::widget_count(self->diagnostics_.eligible_game_thread_calls);
        bool verified_frame=false;
        __try {
            e33_cinematic::ComponentLookupFrame found{};
            if(!self->frame(actor,stack,result,found)) return;
            e33_cinematic::widget_count(self->diagnostics_.exact_frames);
            verified_frame=true;
            const auto track=call_capture(base_,found.track);
            if(!self->widgets_.matches(self->player_,track)) {
                e33_cinematic::widget_count(self->diagnostics_.root_misses);return;
            }
            e33_cinematic::widget_count(self->diagnostics_.owned_matches);
            e33_cinematic::widget_count(self->observed_);
            // Once ownership is established, rejection must return None, never
            // the original gameplay component. No retry after uncertain retain.
            const auto original_result=*reinterpret_cast<uint64_t*>(result);
            *reinterpret_cast<uint64_t*>(result)=0;
            if(self->state_!=1 ||
               original_result==self->resources_[WidgetComponent].address ||
               local_read<uint64_t>(local_read<uint64_t>(found.actor)+0x6f0)!=base_+0x331c4b0 ||
               !private_controls_null(base_,self->resources_[WidgetComponent]) ||
               !self->widgets_.admit(self->player_,track)) {
                self->state_=2;e33_cinematic::widget_count(self->failed_);
                e33_cinematic::widget_count(self->diagnostics_.failed);return;
            }
            *reinterpret_cast<uint64_t*>(result)=self->resources_[WidgetComponent].address;
        } __except(EXCEPTION_EXECUTE_HANDLER) {
            if(verified_frame) {
                *reinterpret_cast<uint64_t*>(result)=0;self->state_=2;
                e33_cinematic::widget_count(self->failed_);
                e33_cinematic::widget_count(self->diagnostics_.failed);
            }
        }
    }
public:
    bool active() const { return state_!=0; }
    bool protects(uint64_t token) const {
        if(!active()) return false;
        for(auto value:tokens_) if(value==token) return true;
        return false;
    }
    // Caller has stopped sequence evaluation before detaching/unhooking.
    uint32_t close(uint64_t base) {
        if(!active()) return 0;
        TargetObjectAssignmentOps context{base};
        if(!context.context()) return 407;
        const auto result=widgets_.close();
        if(result==e33_cinematic::WidgetStep::deferred) return 407;
        if(result!=e33_cinematic::WidgetStep::ok) { state_=2;return 1513; }
        const auto fn=call_identity(base,resources_[WidgetNativeGetter]);
        if(!fn) { state_=2;return 1513; }
        auto slot=reinterpret_cast<void* volatile*>(fn+0xd8);
        auto original_entry=reinterpret_cast<void*>(base+0x333a230);
        auto previous=InterlockedCompareExchangePointer(slot,original_entry,reinterpret_cast<void*>(&route));
        if(previous!=original_entry && previous!=reinterpret_cast<void*>(&route)) { state_=2;return 1513; }
        state_=0;current_=nullptr;return 0;
    }
    template<class Pool,class Sequence>
    void command(uint64_t base,uint64_t session,Pool& leases,Sequence& sequence,CinematicWidgetPacket& p) {
        if(p.version!=1 || !p.owner || p.reserved || p.error || p.state || p.observed || p.failed ||
           p.operation<1 || p.operation>4) { p.error=1510;return; }
        if(p.operation!=1) {
            const auto payload=reinterpret_cast<const uint8_t*>(&p.resources);
            for(size_t i=0;i<sizeof(p)-40;++i) if(payload[i]) { p.error=1511;return; }
            if(p.owner!=owner_) { p.error=1511;return; }
            if(p.operation==2) p.error=close(base);
            if(p.operation==4) {
                if(!active()) { p.error=1511;return; }
                e33_cinematic::widget_diagnostics_payload(&p.resources,sizeof(p)-40,diagnostics_);
            }
        } else {
            if(active() || !sequence.owns_player(p.player)) { p.error=1511;return; }
            for(unsigned i=0;i<WidgetResourceCount;++i)
                if(!call_identity(base,p.resources[i]) || !leases.owns_object(session,p.tokens[i],p.resources[i].address)) {
                    p.error=1511;return; }
            const auto& r=p.resources;uint64_t script{},return_property{};
            if(!cinematic_getter_profile(base,r[WidgetGetter],r[WidgetNativeGetter],r[WidgetLibrary],r[WidgetComponent],script,&return_property)) {
                p.error=1512;return; }
            uint32_t track_diagnostic{};
            if(!cinematic_track_profile(base,r[WidgetGraph],r[WidgetTrackClass],r[WidgetLibrary],r[WidgetComponent],&track_diagnostic)) {
                p.failed=track_diagnostic;p.error=1514;return; }
            if(!cinematic_callback_profile(base,r[WidgetComponent],r[WidgetRegister],r[WidgetUnregister],r[WidgetControls]) ||
               local_read<int32_t>(r[WidgetComponent].address+808) ||
               std::memcmp(&p.remove.function,&r[WidgetRemove],sizeof(CallIdentity))) { p.error=1515;return; }
            HMODULE pinned{};
            if((base_ && base_!=base) || !GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
                    reinterpret_cast<LPCWSTR>(&route),&pinned) ||
               !widgets_.begin(base,session,r[WidgetTrackClass],r[WidgetUserClass],p.remove)) { p.error=1516;return; }
            base_=base;owner_=p.owner;script_=script;return_property_=return_property;player_=p.player;
            std::memcpy(resources_,p.resources,sizeof(resources_));std::memcpy(tokens_,p.tokens,sizeof(tokens_));
            observed_=failed_=0;diagnostics_={};state_=1;current_=this;
            auto slot=reinterpret_cast<void* volatile*>(r[WidgetNativeGetter].address+0xd8);
            auto original_entry=reinterpret_cast<void*>(base+0x333a230);
            if(InterlockedCompareExchangePointer(slot,reinterpret_cast<void*>(&route),original_entry)!=original_entry) {
                const auto closed=widgets_.close();
                state_=closed==e33_cinematic::WidgetStep::ok ? 0 : 2;
                current_=state_ ? this : nullptr;p.error=1516;
            }
        }
        p.state=state_;p.observed=observed_;p.failed=failed_;
    }
};
