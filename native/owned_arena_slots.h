#pragma once
#include <cstdint>
namespace e33_owned_arena {
// Reservations survive failed/unknown construction, even before Owner records
// its token. Only an acknowledged retirement may release a slot.
class Slots {
    uint64_t tokens_[2]{};
public:
    static constexpr unsigned capacity=2;
    int find(uint64_t token)const {
        if(token)for(unsigned i=0;i<capacity;++i)if(tokens_[i]==token)return static_cast<int>(i);
        return -1;
    }
    int reserve(uint64_t token) {
        if(!token||find(token)>=0)return -1; // no prepare replay
        for(unsigned i=0;i<capacity;++i)if(!tokens_[i]){tokens_[i]=token;return static_cast<int>(i);}
        return -1;
    }
    bool reserved(unsigned slot)const{return slot<capacity&&tokens_[slot]!=0;}
    bool retired(unsigned slot,uint32_t error,bool has_work) {
        if(slot>=capacity||error||has_work)return false;
        tokens_[slot]=0;return true;
    }
};
}
