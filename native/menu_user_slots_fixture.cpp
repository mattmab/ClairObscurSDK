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
    uint64_t primary[4]{123,0,0,0}, virtual_user[4]{123,0,0,0};
    slots[0]=reinterpret_cast<uint64_t>(primary);
    slots[16]=reinterpret_cast<uint64_t>(virtual_user);slots[17]=0x1000;
    virtual_user[1]=slots[16];virtual_user[2]=slots[17];virtual_user[3]=uint64_t(8)|(uint64_t(8)<<32);
    assert(menu_primary_user_slots(base,9,28,read));
    virtual_user[3]=9;assert(!menu_primary_user_slots(base,9,28,read));
    virtual_user[3]=uint64_t(8)|(uint64_t(8)<<32);
    slots[2]=slots[16];slots[3]=slots[17];assert(!menu_primary_user_slots(base,9,28,read));
    slots[2]=slots[3]=0;
    reads=0;
    assert(!menu_primary_user_slots(base,17,28,read));
    assert(!menu_primary_user_slots(base,9,8,read));
    assert(!menu_primary_user_slots(base,9,65,read));
    assert(!menu_primary_user_slots(UINT64_MAX-8,9,28,read));
    assert(reads==0);
}
