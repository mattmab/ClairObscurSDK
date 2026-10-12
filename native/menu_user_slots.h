#pragma once
#include <cstdint>
// Slate retains vacant array slots after users disappear. Support one live
// primary user, not one allocated slot. Never accept another occupied slot.
template<class Read>
bool menu_primary_user_slots(uint64_t users, int32_t count, int32_t capacity, Read read) {
    if(!users || count<1 || count>16 || capacity<count || capacity>64 ||
       users>UINT64_MAX-uint64_t(count)*16) return false;
    for(int32_t i=1;i<count;++i)
        if(read(users+uint64_t(i)*16) || read(users+uint64_t(i)*16+8)) return false;
    return true;
}
