#pragma once
#include "menu_action_events.h"

enum class ButtonActionOperation:uint32_t { Bind=1, Drain, Unbind, Status };
enum class ButtonActionOutcome:uint32_t { NotStarted, Unknown, Returned };
constexpr uint32_t kButtonActionCapacity=64;
#pragma pack(push,1)
struct ButtonActionPacket {
    uint32_t version,operation,error,outcome,count,state,reserved[2];
    uint64_t owner,child_lease,action,dropped,registration;
    MenuActionEvent events[kButtonActionCapacity];
};
#pragma pack(pop)
static_assert(sizeof(MenuActionTicket)==32 && sizeof(MenuActionEvent)==40);
static_assert(sizeof(ButtonActionPacket)==2632);
inline bool valid_button_action_request(const ButtonActionPacket& p) {
    if(p.version!=1 || p.operation<1 || p.operation>4 || p.error || p.outcome ||
       p.count || p.state || p.reserved[0] || p.reserved[1] || p.dropped ||
       p.registration || !p.owner || !p.child_lease) return false;
    if((p.operation==static_cast<uint32_t>(ButtonActionOperation::Bind)) != (p.action!=0)) return false;
    for(const auto& e:p.events)
        if(e.ticket.session || e.ticket.registration || e.ticket.owner || e.ticket.action || e.sequence) return false;
    return true;
}
