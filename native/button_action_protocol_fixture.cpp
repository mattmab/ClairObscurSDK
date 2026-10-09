#include "button_action_protocol.h"
#include <cassert>
#include <cstddef>
#include <cstdio>
#include <fstream>

int main(int argc,char** argv) {
    static_assert(offsetof(ButtonActionPacket,events)==72);
    ButtonActionPacket packet{};
    packet.version=1; packet.operation=1; packet.owner=2; packet.child_lease=3; packet.action=4;
    assert(valid_button_action_request(packet));
    auto reject=[&](const ButtonActionPacket& changed) { assert(!valid_button_action_request(changed)); };
    auto changed=packet; changed.version=2; reject(changed);
    changed=packet; changed.operation=0; reject(changed);
    changed=packet; changed.operation=5; reject(changed);
    changed=packet; changed.owner=0; reject(changed);
    changed=packet; changed.child_lease=0; reject(changed);
    changed=packet; changed.action=0; reject(changed);
    changed=packet; changed.error=1; reject(changed);
    changed=packet; changed.outcome=1; reject(changed);
    changed=packet; changed.state=1; reject(changed);
    changed=packet; changed.count=65; reject(changed);
    changed=packet; changed.dropped=1; reject(changed);
    changed=packet; changed.registration=1; reject(changed);
    for(unsigned i=0;i<2;++i) { changed=packet; changed.reserved[i]=1; reject(changed); }
    for(unsigned i=0;i<64;++i) {
        changed=packet; changed.events[i].ticket.session=1; reject(changed);
        changed=packet; changed.events[i].ticket.registration=1; reject(changed);
        changed=packet; changed.events[i].ticket.owner=1; reject(changed);
        changed=packet; changed.events[i].ticket.action=1; reject(changed);
        changed=packet; changed.events[i].sequence=1; reject(changed);
    }
    for(unsigned operation=2;operation<=4;++operation) {
        packet.operation=operation;
        reject(packet); // Action IDs are permitted only in Bind requests.
        packet.action=0; assert(valid_button_action_request(packet)); packet.action=4;
    }
    std::puts("Button action protocol: strict header, operation and output-field rejection passed.");
    if(argc==2) {
        ButtonActionPacket golden{};
        golden.version=1; golden.operation=2; golden.outcome=2; golden.count=1;
        golden.state=2; golden.owner=2; golden.child_lease=3; golden.dropped=2; golden.registration=12;
        golden.events[0]={{7,12,2,4},8};
        std::ofstream output(argv[1],std::ios::binary);
        output.write(reinterpret_cast<const char*>(&golden),sizeof(golden));
        assert(output.good());
    }
}
