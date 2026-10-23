#pragma once
#include "menu_call_contract.h"
enum class MenuOperation : uint32_t { Prepare=1, Attach, Focus, Close, Status, Open
#ifdef E33_RETIRED_WORLD_SESSION
,Retire
#endif
};
enum class MenuOutcome : uint32_t { NotStarted, Unknown, Returned };
#pragma pack(push,1)
struct MenuPacket {
    uint32_t version, operation, error, outcome, active, reserved;
    uint64_t owner, widget_lease, child_lease;
    CallIdentity engine, widget, child, player, library;
    CallPacket plans[kMenuCalls];
};
#pragma pack(pop)
static_assert(sizeof(MenuPacket)==128+sizeof(CallPacket)*kMenuCalls);
inline bool valid_menu_request(const MenuPacket& p) {
    if(p.version!=1 || p.operation<1 || p.operation>
#ifdef E33_RETIRED_WORLD_SESSION
       7
#elif defined(E33_VIEWER_MENU_SESSION)
       6
#else
       5
#endif
        || p.error || p.outcome ||
       p.active || p.reserved || !p.owner) return false;
    if(p.operation!=static_cast<uint32_t>(MenuOperation::Prepare) && p.operation!=static_cast<uint32_t>(MenuOperation::Open)) return true;
    if(!p.widget_lease || !p.child_lease || p.widget_lease==p.child_lease) return false;
    const CallIdentity ids[]={p.engine,p.widget,p.child,p.player,p.library};
    for(const auto& id:ids) if(id.index<0 || id.serial<0 || !id.address) return false;
    for(uint32_t i=0;i<kMenuCalls;++i)
        if(!valid_menu_call(p.plans[i],static_cast<MenuCall>(i))) return false;
    return true;
}
