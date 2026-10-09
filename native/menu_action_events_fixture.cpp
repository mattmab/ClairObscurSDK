#include "menu_action_events.h"
#include <cassert>
#include <cstdio>

int main() {
    MenuActionEvents<3,2> events;
    MenuActionEvent out{};
    assert(!events.open(0) && events.open(7) && !events.open(8));
    assert(!events.bind(8,1,1,100).registration);
    auto a=events.bind(7,1,11,100), b=events.bind(7,2,22,200);
    assert(a.registration && b.registration);
    assert(!events.bind(7,3,33,100).registration);
    assert(!events.begin(999).registration);
    auto forged=a; forged.action=99;
    assert(!events.finish(forged) && !events.revoke(forged));
    assert(events.finish(events.begin(100)) && events.finish(events.begin(200)));
    assert(!events.finish(a)); // Bounded queue reports overflow, never overwrites.
    assert(events.take_dropped(8)==0 && events.take_dropped(7)==1);
    assert(!events.pop(8,out));
    assert(events.revoke(a)); // Also removes queued events; other owners survive.
    assert(events.pop(7,out) && out.ticket.action==22 && out.sequence==2);
    assert(!events.pop(7,out));

    auto replacement=events.bind(7,1,11,100);
    assert(replacement.registration!=a.registration);
    assert(!events.finish(a)); // An original call returning after rebind is stale.
    assert(events.finish(replacement));
    auto during=events.begin(100);
    events.revoke_owner(8,1);
    assert(events.begin(100).registration);
    events.revoke_owner(7,1);
    assert(!events.finish(during) && !events.pop(7,out));
    assert(events.finish(b));
    auto c=events.bind(7,3,33,300), d=events.bind(7,4,44,400);
    assert(c.registration && d.registration && !events.bind(7,5,55,500).registration);
    events.close();
    assert(!events.finish(b) && !events.pop(7,out) && !events.begin(200).registration);
    assert(events.open(7)); // Even a repeated session ID cannot revive old tickets.
    auto next=events.bind(7,2,22,200);
    assert(next.registration!=b.registration && !events.finish(b));
    assert(events.finish(next) && events.pop(7,out) && out.ticket.registration==next.registration);
    assert(out.sequence>2);
    events.close();
    std::puts("Menu action queue: revocation, reentrancy tickets, overflow and session isolation passed.");
}
