#pragma once
#include "trace_slots.h"
#include "blueprint_argument_transform.h"

// Build 23765773 direct Blueprint opcode, independently analyzed in Ghidra:
// 1413986b0 consumes an 8-byte UFunction operand, then 14138ee60 builds and
// destroys the callee frame. We substitute only its interpreter callback.
// All other opcodes and functions forward to the exact original entry.
inline thread_local bool blueprint_direct_frame = false;
class BlueprintDirectTrace {
    inline static uint64_t base_{}; // immutable while a stale wrapper can exist
    inline static void* volatile* slots_[256]{};
    inline static void* originals_[256]{};
    inline static void* wrappers_[256]{};
    inline static uint64_t damage_name_{};
    inline static uint64_t new_game_name_{};
    inline static uint64_t external_names_[2]{};
    inline static bool external_{};
    inline static uint64_t completion_name_{};
    inline static uint64_t modifier_name_{};
    inline static uint64_t inworld_names_[2]{};
    inline static uint64_t story_action_name_{};
    inline static uint64_t narrative_names_[64]{};
    inline static unsigned count_{};
    static void observe(uint64_t function,void* object,void* frame,void* result,bool before,size_t post_handle=0) {
        const bool previous=blueprint_direct_frame;
        blueprint_direct_frame=true;
        __try {
            auto* address=reinterpret_cast<void* volatile*>(function+0xd8);
            if(before) e33_trace::TraceSlots<>::observe_entry(address,object,frame,result);
            else e33_trace::TraceSlots<>::observe_post(post_handle,address,object,frame,result);
        } __finally {blueprint_direct_frame=previous;}
    }
    static void __fastcall body(void* object, void* frame, void* result) {
        uint64_t function{};
        const bool selected=target_trace_read(reinterpret_cast<uint64_t>(frame)+0x10,&function,8) &&
            function && function<=UINT64_MAX-0xd8;
        const auto post_handle=selected ? e33_trace::TraceSlots<>::post_observation(
            reinterpret_cast<void* volatile*>(function+0xd8)) : 0;
        if(selected) observe(function,object,frame,result,true);
        const auto transform=e33_blueprint_transform::find(function);
        e33_blueprint_transform::Decision decision;
        if(selected&&transform.owner)decision=transform.begin(transform.owner,function,object,frame);
        if(!decision.skip)reinterpret_cast<e33_trace::Entry>(base_+0x13938a0)(object,frame,result);
        if(decision.token&&transform.end)transform.end(transform.owner,decision.token);
        // Build() still owns this callee frame. Copy only after the original
        // interpreter returned, before Build destroys temporary parameters.
        if(post_handle) observe(function,object,frame,result,false,post_handle);
    }
    static bool selected(void* frame, uint64_t& code, uint64_t& function) {
        const auto address=reinterpret_cast<uint64_t>(frame);
        return address && address <= UINT64_MAX-0x28 &&
            target_trace_read(address+0x20,&code,8) && code <= UINT64_MAX-8 &&
            target_trace_read(code,&function,8) && function && function <= UINT64_MAX-0xd8 &&
            (e33_trace::TraceSlots<>::observes_entry(reinterpret_cast<void* volatile*>(function+0xd8))||
             e33_blueprint_transform::selected(function));
    }
    static void __fastcall route(void* object, void* frame, void* result) {
        uint64_t code{}, function{};
        if (selected(frame,code,function)) {
            // The original opcode makes this same write before argument evaluation.
            const auto next=code+8;
            std::memcpy(static_cast<uint8_t*>(frame)+0x20,&next,8);
            using Build=void(__fastcall*)(void*,uint64_t,void*,void*,e33_trace::Entry);
            reinterpret_cast<Build>(base_+0x138ee60)(object,function,frame,result,body);
        } else reinterpret_cast<e33_trace::Entry>(base_+0x13986b0)(object,frame,result);
    }
    // Named opcode 141398850: comparison index at +0 and number at +8
    // form the compact FName passed in RDX to 141391a40 (RCX is object).
    // Only the verified damage name incurs a lookup; other calls stay original.
    static void __fastcall named_route(void* object, void* frame, void* result) {
        const auto address=reinterpret_cast<uint64_t>(frame);
        uint64_t code{};
        uint32_t name[3]{};
        if (address && address<=UINT64_MAX-0x28 &&
            target_trace_read(address+0x20,&code,8) && code && code<=UINT64_MAX-12 &&
            target_trace_read(code,name,12) &&
            matches_name(uint64_t(name[0]) | (uint64_t(name[2])<<32))) {
            using Find=uint64_t(__fastcall*)(void*,uint64_t);
            const auto function=reinterpret_cast<Find>(base_+0x1391a40)(object,uint64_t(name[0]) | (uint64_t(name[2])<<32));
            if (function && function<=UINT64_MAX-0xd8 &&
                (e33_trace::TraceSlots<>::observes_entry(reinterpret_cast<void* volatile*>(function+0xd8))||
                 e33_blueprint_transform::selected(function))) {
                const auto next=code+12;
                std::memcpy(static_cast<uint8_t*>(frame)+0x20,&next,8);
                using Build=void(__fastcall*)(void*,uint64_t,void*,void*,e33_trace::Entry);
                reinterpret_cast<Build>(base_+0x138ee60)(object,function,frame,result,body);
                return;
            }
        }
        reinterpret_cast<e33_trace::Entry>(base_+0x1398850)(object,frame,result);
    }
public:
#ifdef E33_TRACE_ROUTING_FIXTURE
    static void fixture_body(uint64_t base,void* object,void* frame,void* result) {
        base_=base;body(object,frame,result);
    }
#endif
    static bool matches_name(uint64_t name){
        for(const auto value:narrative_names_)if(value&&value==name)return true;
        return name&&((damage_name_&&damage_name_==name)||
        (external_&&(external_names_[0]==name||external_names_[1]==name))||new_game_name_==name||completion_name_==name||modifier_name_==name||story_action_name_==name||inworld_names_[0]==name||inworld_names_[1]==name);}
    static bool retain_narrative(uint64_t base,uint64_t function){
        if(!function)return false;
        const auto old=damage_name_;
        if(!count_&&!install(base,function))return false;
        if(base_!=base)return false;
        const auto name=local_read<uint64_t>(function+24);damage_name_=old;if(!name)return false;
        for(const auto value:narrative_names_)if(value==name)return false;
        for(auto&value:narrative_names_)if(!value){value=name;return true;}return false;
    }
    static bool release_narrative(uint64_t function){
        const auto name=local_read<uint64_t>(function+24);bool found=false;
        for(auto&value:narrative_names_)if(value==name){value=0;found=true;}
        return found&&(damage_name_?true:close());
    }
    static bool retain_story_action(uint64_t base,uint64_t function){
        if(story_action_name_||!function)return false;
        const auto old=damage_name_;
        if(!count_&&!install(base,function))return false;
        if(base_!=base)return false;
        story_action_name_=local_read<uint64_t>(function+24);damage_name_=old;return story_action_name_!=0;
    }
    static bool release_story_action(){story_action_name_=0;return damage_name_?true:close();}
    static bool retain_inworld(uint64_t base,uint64_t finished,uint64_t interrupted){
        if(inworld_names_[0]||inworld_names_[1]||!finished||!interrupted)return false;
        const auto old=damage_name_;
        if(!count_&&!install(base,finished))return false;
        if(base_!=base)return false;
        inworld_names_[0]=local_read<uint64_t>(finished+24);inworld_names_[1]=local_read<uint64_t>(interrupted+24);
        damage_name_=old;return inworld_names_[0]&&inworld_names_[1];
    }
    static bool release_inworld(){inworld_names_[0]=inworld_names_[1]=0;return damage_name_?true:close();}
    static bool retain_modifier(uint64_t base,uint64_t function) {
        if(modifier_name_ || base_!=base || !count_ || !function)return false;
        modifier_name_=local_read<uint64_t>(function+24);return modifier_name_!=0;
    }
    static void release_modifier(){modifier_name_=0;}
    // Exact completion owner validates its function/controller schema first.
    // This only retains shared opcode routing; its POST slot remains separate.
    static bool retain_completion(uint64_t base,uint64_t function) {
        uint64_t name{};
        if(completion_name_ || !function || function>UINT64_MAX-24 ||
           !target_trace_read(function+24,&name,8) || !name) return false;
        const auto old=damage_name_;
        if(!count_ && !install(base,function)) return false;
        if(base_!=base) return false;
        completion_name_=name;damage_name_=old;return true;
    }
    static bool release_completion() {
        completion_name_=0;return damage_name_ ? true : close();
    }
    // Separate SDK owner for the two bounded encounter callbacks. Trace expiry
    // must not detach this owner's shared opcode routing.
    static bool retain_encounter(uint64_t base,uint64_t spawn,uint64_t difficulty){
        if(external_||!spawn||!difficulty)return false;
        const auto old=damage_name_;
        if(!count_&&!install(base,spawn))return false;
        if(base_!=base)return false;
        external_names_[0]=local_read<uint64_t>(spawn+24);
        external_names_[1]=local_read<uint64_t>(difficulty+24);
        external_=true;damage_name_=old;
        return true;
    }
    static bool release_encounter(){external_=false;external_names_[0]=external_names_[1]=0;return damage_name_?true:close();}
    static bool original_direct_or_owned(uint64_t base,uint64_t pointer){
        return pointer==base+0x13986b0||(base_==base&&count_&&pointer==reinterpret_cast<uint64_t>(&route));
    }
    static bool install(uint64_t base, uint64_t function) {
        if (base_ && base_!=base) return false;
        uint64_t name{};
        if (!function || function>UINT64_MAX-0x20 ||
            !target_trace_read(function+0x18,&name,8) || !name) return false;
        const bool menu=exact_name(base,function+24,"OnStartGameSettingsApplied");
        if (count_) {
            if(menu){if(new_game_name_&&new_game_name_!=name)return false;new_game_name_=name;}
            else {if(damage_name_&&damage_name_!=name)return false;damage_name_=name;}
            return true;
        }
        HMODULE pinned{};
        if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
            reinterpret_cast<LPCWSTR>(&route),&pinned)) return false;
        base_=base;
        if(menu)new_game_name_=name;else damage_name_=name;
        unsigned direct_count=0, named_count=0;
        for (unsigned i=0;i<256;++i) {
            auto slot=reinterpret_cast<void* volatile*>(base+0x9360600+i*8);
            for (unsigned kind=0;kind<2;++kind) {
                auto expected=reinterpret_cast<void*>(base+(kind ? 0x1398850 : 0x13986b0));
                auto wrapper=kind ? reinterpret_cast<void*>(&named_route) : reinterpret_cast<void*>(&route);
                if (InterlockedCompareExchangePointer(slot,wrapper,expected)==expected) {
                    slots_[count_]=slot; originals_[count_]=expected; wrappers_[count_++]=wrapper;
                    if (kind) ++named_count; else ++direct_count;
                }
            }
        }
        if (direct_count && named_count) return true;
        close(); return false;
    }
    static bool close() {
        damage_name_=0;
        new_game_name_=0;
        for(const auto value:narrative_names_)if(value)return true;
        if(external_ || completion_name_ || modifier_name_ || story_action_name_ || inworld_names_[0] || inworld_names_[1])return true;
        bool ok=true;
        while(count_) {
            auto slot=slots_[--count_];
            const auto old=InterlockedCompareExchangePointer(slot,originals_[count_],wrappers_[count_]);
            ok &= old==wrappers_[count_] || old==originals_[count_];
        }
        return ok;
    }
};
