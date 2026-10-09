#pragma once
#include "menu_lifetime.h"
#include "menu_call_contract.h"
#include "target_menu_focus.h"
#include "strong_lease_pool.h"
#include "menu_session.h"
#ifdef E33_MULTI_BUTTON_SESSION
#include "target_multi_button_actions.h"
#endif
#ifdef E33_BUTTON_REFERENCE_SESSION
#include "target_button_reference.h"
#endif
#ifdef E33_BUTTON_ACTION_SESSION
#ifndef E33_BUTTON_REFERENCE_SESSION
#error Button actions require retained SButton ownership
#endif
#include "target_button_actions.h"
#endif

// Candidate only. Copy verified request data here before touching the engine;
// never retain a pointer into IPC. The containing runtime owns this storage and
// contains SEH around every operation. No v14 transport is installed yet.
struct TargetMenuStorage {
    uint64_t base=0, session=0, owner=0, widget_lease=0, child_lease=0;
    CallIdentity widget{-1,0,0}, child{-1,0,0}, player{-1,0,0}, library{-1,0,0};
    CallPacket plans[kMenuCalls]{};
    TargetMenuFocusOwner focus;
#ifdef E33_BUTTON_REFERENCE_SESSION
    TargetButtonReference child_slate;
#endif
#ifdef E33_BUTTON_ACTION_SESSION
    TargetButtonActions actions;
#endif
    CallIdentity engine{-1,0,0};
    MenuSession menu;
#ifdef E33_MULTI_BUTTON_SESSION
    TargetMultiButtonActions multi_actions;
#endif
};
template<class Pool>
struct TargetMenuOps {
    TargetMenuStorage& data;
    Pool& leases;
    bool exact_class(uint64_t object,const char* name,const char* package) const {
        if(!call_capture(data.base,object).address) return false;
        auto cls=local_read<uint64_t>(object+0x10);
        return call_is_class(data.base,cls) && exact_name(data.base,cls+0x18,name) &&
            exact_name(data.base,local_read<uint64_t>(cls+0x20)+0x18,package);
    }
    bool objects_valid() const {
        auto base=data.base;
        if(!call_identity(base,data.widget) || !call_identity(base,data.child) ||
           !call_identity(base,data.player) || !call_identity(base,data.library) ||
           !leases.owns_object(data.session,data.widget_lease,data.widget.address) ||
           !leases.owns_object(data.session,data.child_lease,data.child.address)) return false;
        if(!exact_class(data.widget.address,"CommonActivatableWidget","/Script/CommonUI") ||
           !exact_class(data.child.address,"Button","/Script/UMG") ||
           !exact_class(data.library.address,"WidgetBlueprintLibrary","/Script/UMG") ||
           !exact_name(base,data.library.address+0x18,"Default__WidgetBlueprintLibrary") ||
           !(local_read<uint32_t>(data.library.address+8)&0x10) ||
           (local_read<uint32_t>(data.widget.address+8)&(0x10|0x40000000)) ||
           (local_read<uint32_t>(data.child.address+8)&(0x10|0x40000000)) ||
           local_read<uint64_t>(data.widget.address+0x310)) return false;
        auto tree=local_read<uint64_t>(data.child.address+0x20);
        return exact_class(tree,"WidgetTree","/Script/UMG") &&
            local_read<uint64_t>(tree+0x20)==data.widget.address;
    }
    MenuContext context() const {
        auto base=data.base;
        if(!base || GetCurrentThreadId()!=local_read<DWORD>(base+0x9272d30) ||
           local_read<uint8_t>(base+0x9272cea)) return MenuContext::Terminal;
        if(local_read<uint8_t>(base+0x9272cfc) || local_read<uint8_t>(base+0x934e968))
            return MenuContext::Deferred;
        return objects_valid() ? MenuContext::Ready : MenuContext::Terminal;
    }
    CallIdentity target(MenuCall op) const {
        if(op==MenuCall::Restore) return data.library;
        if(op==MenuCall::SetFocus || op==MenuCall::KeyboardFocus || op==MenuCall::UserFocus)
            return data.child;
        return data.widget;
    }
    bool plan_valid(MenuCall op) const {
        auto index=static_cast<uint32_t>(op);
        if(index>=kMenuCalls) return false;
        const auto& p=data.plans[index];
        auto* spec=menu_call_spec(op);
        auto fn=call_identity(data.base,p.function);
        if(!fn || !valid_menu_call(p,op) || !menu_same_identity(p.target,target(op)) ||
           !exact_name(data.base,fn+0x18,spec->name)) return false;
        auto owner=local_read<uint64_t>(fn+0x20);
        if(!exact_name(data.base,owner+0x18,spec->owner) ||
           !exact_name(data.base,local_read<uint64_t>(owner+0x20)+0x18,
                       spec->rva>=0x4790000 ? "/Script/CommonUI" : "/Script/UMG")) return false;
        if(op==MenuCall::SetFocus || op==MenuCall::UserFocus)
            if(!menu_same_identity(p.objects[0].identity,data.player)) return false;
        return true;
    }
    bool prior_target_valid() const {
        TargetMenuFocusSnapshot current{};
        return data.focus.observe(data.base,current);
    }
    bool validate_owned(uint64_t session,uint64_t owner,uint64_t widget,uint64_t child) const {
        return prior_target_valid() && validate_preparation(session,owner,widget,child);
    }
    bool validate_preparation(uint64_t session,uint64_t owner,uint64_t widget,uint64_t child) const {
        if(session!=data.session || owner!=data.owner || widget!=data.widget_lease ||
           child!=data.child_lease || context()!=MenuContext::Ready) return false;
        for(uint32_t i=0;i<kMenuCalls;++i) {
            if(!plan_valid(static_cast<MenuCall>(i))) return false;
            auto packet=data.plans[i];
            if(reflected_call(data.base,packet,nullptr,nullptr,nullptr,nullptr,true) ||
               packet.outcome!=CallNotDispatched) return false;
        }
        return true;
    }
    MenuResult capture_baseline() {
        auto result=data.focus.capture(data.base,data.engine);
        return result==SlateReferenceResult::Ok ? MenuResult::Ok : MenuResult::Invalid;
    }
    MenuResult release_prepared_baseline() {
        auto result=data.focus.release(data.base);
        if(result==SlateReferenceResult::Ok) return MenuResult::Ok;
        if(result==SlateReferenceResult::Deferred) return MenuResult::Deferred;
        return MenuResult::Quarantined;
    }
    bool invoke(MenuCall op,bool* result=nullptr) {
        if(context()!=MenuContext::Ready || !plan_valid(op)) return false;
        // Local packet is only a transient dispatch buffer. All lifecycle and
        // prior-focus ownership is already durable in data before this call.
        auto packet=data.plans[static_cast<uint32_t>(op)];
        auto error=reflected_call(data.base,packet);
        if(error || packet.outcome!=CallDispatchReturned) return false;
        if(result) {
            if(packet.return_offset>=kCallBytes || packet.data[packet.return_offset]>1) return false;
            *result=packet.data[packet.return_offset]!=0;
        }
        return true;
    }
    bool check(MenuCall op,bool expected) {
        bool value=false; return invoke(op,&value) && value==expected;
    }
    bool attach() {
        const bool attached=focus_owner()==MenuFocusOwner::Prior &&
            check(MenuCall::InViewport,false) && check(MenuCall::Active,false) &&
            invoke(MenuCall::Add) && check(MenuCall::InViewport,true) &&
            invoke(MenuCall::Activate) && check(MenuCall::Active,true);
#ifdef E33_BUTTON_REFERENCE_SESSION
        return attached && data.child_slate.capture(data.base,data.child)==SlateReferenceResult::Ok &&
            data.child_slate.unchanged(data.base);
#else
        return attached;
#endif
    }
    bool focus() {
        auto current=focus_owner();
        return (current==MenuFocusOwner::Prior || current==MenuFocusOwner::Owned) &&
            invoke(MenuCall::SetFocus) &&
            check(MenuCall::KeyboardFocus,true) && check(MenuCall::UserFocus,true);
    }
    MenuFocusOwner focus_owner() {
        TargetMenuFocusSnapshot current{};
        if(!data.focus.observe(data.base,current)) return MenuFocusOwner::Invalid;
        if(current.focused==current.viewport && current.focused_controller==current.viewport_controller)
            return MenuFocusOwner::Prior;
        bool keyboard=false, user=false;
        if(!invoke(MenuCall::KeyboardFocus,&keyboard) || !invoke(MenuCall::UserFocus,&user) ||
           keyboard!=user) return MenuFocusOwner::Invalid;
        return user ? MenuFocusOwner::Owned : MenuFocusOwner::Unrelated;
    }
    bool restore() {
        auto current=focus_owner();
        if(current==MenuFocusOwner::Prior || current==MenuFocusOwner::Unrelated) return true;
        return current==MenuFocusOwner::Owned && prior_target_valid() && invoke(MenuCall::Restore) &&
            focus_owner()==MenuFocusOwner::Prior;
    }
    bool deactivate() { return invoke(MenuCall::Deactivate) && check(MenuCall::Active,false); }
    bool detach() { return invoke(MenuCall::Remove) && check(MenuCall::InViewport,false); }
    bool release_baseline() {
#ifdef E33_BUTTON_REFERENCE_SESSION
        if(data.child_slate.release(data.base)!=SlateReferenceResult::Ok) return false;
#endif
        return data.focus.release(data.base)==SlateReferenceResult::Ok;
    }
};
