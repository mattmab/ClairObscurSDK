#pragma once
#include "button_action_protocol.h"
#include "invocation_protocol.h"

// Separate v17 packet: control-specific bind/remove/status and one menu-wide
// drain. Only Bind accepts a copied UObject identity; no delegate address input.
#pragma pack(push,1)
struct MultiButtonPacket {
    ButtonActionPacket action;
    CallIdentity child;
};
#pragma pack(pop)
static_assert(sizeof(MultiButtonPacket)==2648);
inline bool valid_multi_button_request(const MultiButtonPacket& p) {
    const auto& a=p.action;
    if(a.version!=1 || a.operation<1 || a.operation>4 || !a.owner || a.error || a.outcome ||
       a.count || a.state || a.reserved[0] || a.reserved[1] || a.dropped || a.registration) return false;
    const bool bind=a.operation==1, drain=a.operation==2;
    if(bind!=(a.action!=0) || drain==(a.child_lease!=0)) return false;
    if(bind) {
        if(p.child.index<0 || p.child.serial<=0 || p.child.address<0x10000 || (p.child.address&7)) return false;
    } else if(p.child.index!=-1 || p.child.serial || p.child.address) return false;
    for(const auto& e:a.events)
        if(e.ticket.session || e.ticket.registration || e.ticket.owner || e.ticket.action || e.sequence) return false;
    return true;
}
