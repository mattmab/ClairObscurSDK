#pragma once
#include "target_slate_reference.h"
#include "menu_user_slots.h"

struct TargetMenuFocusSnapshot {
    uint64_t application=0, user=0, user_controller=0;
    uint64_t viewport=0, viewport_controller=0, focused=0, focused_controller=0;
};

// Bounded game-thread observation. This alone does not own any Slate reference.
// The caller must contain SEH and reject snapshots on failure, not synthesize
// a viewport baseline. No stock engine offsets are used.
inline bool target_menu_focus_snapshot(uint64_t base,const CallIdentity& engine,
                                       TargetMenuFocusSnapshot& result,uint32_t* diagnostic=nullptr) {
    result={};
    if(diagnostic)*diagnostic=90201;
    TargetSlateReferenceOps refs{base};
    if(!refs.can_release() || !call_identity(base,engine)) return false;
    if(diagnostic)*diagnostic=90202;
    auto engine_class=local_read<uint64_t>(engine.address+0x10);
    if(!exact_name(base,engine_class+0x18,"GameEngine") ||
       !exact_name(base,local_read<uint64_t>(engine_class+0x20)+0x18,"/Script/Engine") ||
       (local_read<uint32_t>(engine.address+8)&(0x10|0x40000000))) return false;
    TargetMenuFocusSnapshot snapshot{};
    snapshot.application=local_read<uint64_t>(base+0x938d218);
    auto app=snapshot.application;
    if(diagnostic)*diagnostic=90203;
    if(!app || app!=local_read<uint64_t>(base+0x93652a0) ||
       local_read<uint64_t>(app)!=base+0x6e5f0d8) return false;
    auto mapping=local_read<uint64_t>(app+0x690);
    if(diagnostic)*diagnostic=90204;
    if(!mapping || local_read<uint64_t>(mapping)!=base+0x6e5f098 ||
       local_read<uint64_t>(base+0x6e5f0a0)!=base+0x10044d0) return false;
    auto users=local_read<uint64_t>(app+0x2f8);
    auto count=local_read<int32_t>(app+0x300), capacity=local_read<int32_t>(app+0x304);
    if(diagnostic)*diagnostic=90205;
    if(!menu_primary_user_slots(users,count,capacity,
        [](uint64_t address) { return local_read<uint64_t>(address); })) return false;
    snapshot.user=local_read<uint64_t>(users);
    snapshot.user_controller=local_read<uint64_t>(users+8);
    if(diagnostic)*diagnostic=90206;
    if(!snapshot.user || !snapshot.user_controller ||
       local_read<LONG>(snapshot.user_controller+8)<=0) return false;
    snapshot.viewport=local_read<uint64_t>(engine.address+0x10d0);
    snapshot.viewport_controller=local_read<uint64_t>(engine.address+0x10d8);
    if(diagnostic)*diagnostic=90207;
    if(!refs.known_reference(snapshot.viewport,snapshot.viewport_controller) ||
       snapshot.viewport!=local_read<uint64_t>(app+0x398) ||
       snapshot.viewport_controller!=local_read<uint64_t>(app+0x3a0)) return false;
    auto path=local_read<uint64_t>(snapshot.user+0x70);
    auto path_count=local_read<int32_t>(snapshot.user+0x78);
    auto path_capacity=local_read<int32_t>(snapshot.user+0x7c);
    if(diagnostic)*diagnostic=90208;
    if(path_count<0 || path_count>path_capacity || path_capacity>128) return false;
    if(path_count) {
        if(diagnostic)*diagnostic=90209;
        if(!path) return false;
        auto last=path+uint64_t(path_count-1)*16;
        auto controller=local_read<uint64_t>(last+8);
        if(controller && local_read<LONG>(controller+8)>0) {
            snapshot.focused=local_read<uint64_t>(last);
            snapshot.focused_controller=controller;
        }
    }
    result=snapshot;
    if(diagnostic)*diagnostic=0;
    return true;
}

// Captured native storage outlives the Python controller. Holding the concrete
// viewport reference prevents its address/controller storage from being reused.
struct TargetMenuFocusOwner {
    CallIdentity engine{-1,0,0};
    TargetMenuFocusSnapshot baseline{};
    OwnedSlateReference viewport;
    uint32_t capture_diagnostic=0;

    SlateReferenceResult capture(uint64_t base,const CallIdentity& engine_identity) {
        capture_diagnostic=90210;
        if(viewport.state!=SlateReferenceState::Empty) return SlateReferenceResult::Busy;
        TargetMenuFocusSnapshot found{};
        if(!target_menu_focus_snapshot(base,engine_identity,found,&capture_diagnostic))
            return SlateReferenceResult::Invalid;
        capture_diagnostic=90220;
        if(found.focused!=found.viewport || found.focused_controller!=found.viewport_controller)
            return SlateReferenceResult::Invalid;
        // Publish all restoration identities before entering ownership code.
        engine=engine_identity; baseline=found;
        TargetSlateReferenceOps refs{base};
        capture_diagnostic=90230;
        auto result=retain_slate_reference(refs,viewport,found.viewport,found.viewport_controller);
        if(result==SlateReferenceResult::Ok)capture_diagnostic=0;
        return result;
    }
    bool observe(uint64_t base,TargetMenuFocusSnapshot& current) const {
        return viewport.state==SlateReferenceState::Live &&
            target_menu_focus_snapshot(base,engine,current) &&
            current.application==baseline.application && current.user==baseline.user &&
            current.user_controller==baseline.user_controller &&
            current.viewport==viewport.widget && current.viewport_controller==viewport.controller;
    }
    SlateReferenceResult release(uint64_t base) {
        TargetSlateReferenceOps refs{base};
        auto result=release_slate_reference(refs,viewport);
        if(result==SlateReferenceResult::Ok) { engine={-1,0,0}; baseline={}; }
        return result;
    }
};
