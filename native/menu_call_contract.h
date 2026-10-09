#pragma once
#include "invocation_protocol.h"

enum class MenuCall : uint32_t { Add, InViewport, Activate, Active, SetFocus,
    KeyboardFocus, UserFocus, Deactivate, Remove, Restore, Count };
constexpr uint32_t kMenuCalls=static_cast<uint32_t>(MenuCall::Count);
struct MenuCallSpec { const char* owner; const char* name; uint32_t rva, size, count, result; };
inline const MenuCallSpec* menu_call_spec(MenuCall call) {
    static constexpr MenuCallSpec specs[] = {
        {"UserWidget","AddToViewport",0x31355b0,4,1,65535},
        {"Widget","IsInViewport",0x31008b0,1,1,0},
        {"CommonActivatableWidget","ActivateWidget",0x4795d00,0,0,65535},
        {"CommonActivatableWidget","IsActivated",0x4799bd0,1,1,0},
        {"Widget","SetUserFocus",0x310c1e0,8,1,65535},
        {"Widget","HasKeyboardFocus",0x31000d0,1,1,0},
        {"Widget","HasUserFocus",0x31004b0,9,2,8},
        {"CommonActivatableWidget","DeactivateWidget",0x4796d40,0,0,65535},
        {"Widget","RemoveFromParent",0x31018d0,0,0,65535},
        {"WidgetBlueprintLibrary","SetFocusToGameViewport",0x313faf0,0,0,65535}
    };
    auto index=static_cast<uint32_t>(call);
    return index<kMenuCalls ? &specs[index] : nullptr;
}
inline bool menu_same_identity(const CallIdentity& a,const CallIdentity& b) {
    return a.index==b.index && a.serial==b.serial && a.address==b.address;
}
// Pure candidate contract. reflected_call additionally verifies every live
// FProperty and UFunction before dispatch; this is not a substitute for it.
inline bool valid_menu_call(const CallPacket& p,MenuCall call) {
    auto* spec=menu_call_spec(call);
    if(!spec || validate_call_packet(p) || p.version!=kCallVersion ||
       p.entry_rva!=spec->rva || p.parameter_size!=spec->size ||
       p.return_offset!=spec->result || p.field_count!=spec->count ||
       !(p.function_flags&0x400)) return false;
    const bool player=call==MenuCall::SetFocus || call==MenuCall::UserFocus;
    if(p.object_count!=(player ? 1u : 0u)) return false;
    for(uint32_t i=0;i<p.field_count;++i) {
        const auto& f=p.fields[i];
        if(f.dimension!=1) return false;
        if(player && i==0) {
            if(f.kind!=CallObject || f.offset || f.width!=8 ||
               std::strcmp(f.name,"PlayerController") || (f.flags&0x500) ||
               p.objects[0].offset) return false;
        } else if(call==MenuCall::Add) {
            int32_t order=0; std::memcpy(&order,p.data,4);
            if(f.kind!=CallInt32 || f.offset || f.width!=4 ||
               std::strcmp(f.name,"ZOrder") || (f.flags&0x500) || order<0 || order>10000) return false;
        } else if(f.kind!=CallBool || f.offset!=spec->result || f.width!=1 ||
                  f.bool_encoding!=0xff010001 || !(f.flags&0x400) ||
                  std::strcmp(f.name,"ReturnValue")) return false;
    }
    return true;
}
