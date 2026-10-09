#include "multi_button_protocol.h"
#include <cassert>
#include <cstdio>
int main() {
    MultiButtonPacket packet{};
    auto& a=packet.action;
    a.version=1; a.operation=1; a.owner=1; a.child_lease=2; a.action=3;
    packet.child={4,5,0x10000};
    assert(valid_multi_button_request(packet));
    auto good=packet;
    packet.child.serial=0; assert(!valid_multi_button_request(packet)); packet=good;
    packet.child.address++; assert(!valid_multi_button_request(packet)); packet=good;
    a.registration=1; assert(!valid_multi_button_request(packet)); packet=good;
    a.events[63].sequence=1; assert(!valid_multi_button_request(packet)); packet=good;
    a.version=2; assert(!valid_multi_button_request(packet)); packet=good;
    a.operation=2; a.action=0; a.child_lease=0; packet.child={-1,0,0};
    assert(valid_multi_button_request(packet));
    a.child_lease=2; assert(!valid_multi_button_request(packet));
    a.operation=3; assert(valid_multi_button_request(packet));
    packet.child=good.child; assert(!valid_multi_button_request(packet));
    packet.child={-1,0,0}; a.operation=4; assert(valid_multi_button_request(packet));
    a.action=3; assert(!valid_multi_button_request(packet));
    std::puts("Multi-button packet bind identity, menu-wide drain and output rejection passed.");
}
