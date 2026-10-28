#pragma once
#include "invocation_protocol.h"
constexpr uint32_t SessionMediaOwner=114;
#pragma pack(push,1)
struct MediaOwnerPacket {
    uint32_t version,operation;
    uint64_t owner,lease;
    uint32_t error,state;
    CallPacket close,remove;
};
#pragma pack(pop)
static_assert(sizeof(MediaOwnerPacket)==49328);

// Bounded state machine shared with the native fixture. A mutation is never
// repeated after an unknown outcome. Only confirmed pre-dispatch GC defers.
struct MediaCleanupState {
    uint32_t state=0, step=0;
    uint32_t retire(bool positively_retired,bool owned_storage) {
        if(!state)return 0;
        if(state==2)return 1403;
        if(!positively_retired)return 1404;
        if(!owned_storage)return 1403;
        // Deliberately no Ops/dispatcher: the retired World owns destruction.
        state=0;step=2;return 0;
    }
    template<class Ops> uint32_t close(Ops& ops) {
        if(!state) return 0;
        if(state==2) return 1403;
        while(step<2) {
            state=2;
            const auto result=ops.invoke(step);
            if(result==407) { state=1; return 407; }
            if(result) return 1403;
            ++step; state=1;
        }
        state=0; return 0;
    }
};
