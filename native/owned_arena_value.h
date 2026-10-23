#pragma once
#include <cstdint>

namespace e33_enemy_spawn {
// Fixed supported-build soft-reference storage. Engine operations own its
// string allocations; never copy its bytes into another owning value.
struct OwnedArenaValue {
    alignas(8) uint8_t bytes[40]{};
    bool live=false;
    template<class Copy> bool assign(Copy&& copy,const void* source){
        if(live||!source)return false;
        live=true; // retained even if the engine copy throws
        copy(bytes,source);return true;
    }
    template<class Ready,class Copy> bool close(Ready&& ready,Copy&& copy){
        if(!live)return true;
        if(!ready())return false;
        const uint8_t empty[40]{};copy(bytes,empty);
        live=false;return true;
    }
};
}
