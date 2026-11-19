#pragma once
#include <cstdint>
// Slate retains vacant array slots after users disappear. Support one live
// primary user, not one allocated slot. Slots 8+ may contain game-created
// virtual users; verify their self/controller/index tuple without changing them.
template<class Read>
bool menu_primary_user_slots(uint64_t users, int32_t count, int32_t capacity, Read read) {
    if(!users || count<1 || count>16 || capacity<count || capacity>64 ||
       users>UINT64_MAX-uint64_t(count)*16) return false;
    for(int32_t i=1;i<count;++i) {
        auto user=read(users+uint64_t(i)*16), controller=read(users+uint64_t(i)*16+8);
        if(!user && !controller)continue;
        if(i<8 || !user || !controller || (user&7) || (controller&7))return false;
        auto primary=read(users);
        if(!primary || read(user)!=read(primary) || read(user+8)!=user ||
           read(user+16)!=controller ||
           read(user+24)!=(uint64_t(i)|(uint64_t(i)<<32)))return false;
    }
    return true;
}
