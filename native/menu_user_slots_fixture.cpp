#include "menu_user_slots.h"
#include <cassert>
int main() {
    uint64_t slots[32]{};
    const auto base=reinterpret_cast<uint64_t>(slots);
    unsigned reads=0;
    auto read=[&](uint64_t p) { ++reads; return *reinterpret_cast<uint64_t*>(p); };
    assert(menu_primary_user_slots(base,9,28,read));
    assert(reads==16);
    slots[16]=1;
    assert(!menu_primary_user_slots(base,9,28,read));
    slots[16]=0; slots[17]=1;
    assert(!menu_primary_user_slots(base,9,28,read));
    reads=0;
    assert(!menu_primary_user_slots(base,17,28,read));
    assert(!menu_primary_user_slots(base,9,8,read));
    assert(!menu_primary_user_slots(base,9,65,read));
    assert(!menu_primary_user_slots(UINT64_MAX-8,9,28,read));
    assert(reads==0);
}
