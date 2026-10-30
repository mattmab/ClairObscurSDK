#pragma once
#include "sequence_seek_protocol.h"
#include "sequence_seek_schema.h"
#include "target_pod_schema.h"

struct TargetSequenceSeekOps:TargetPodSchemaOps {
    bool registered(uint64_t p) const {return identity(capture(p));}
    bool is_class(uint64_t p) const {return call_is_class(base,p);}
};

inline bool sequence_seek_target(TargetSequenceSeekOps& ops,const CallIdentity& player,const CallIdentity& actor,
                                 const SequenceSeekPacket& p) {
    if(!ops.context() || !ops.identity(player) || !ops.identity(actor) ||
       (ops.read<uint32_t>(player.address+8)&0x10) || (ops.read<uint32_t>(actor.address+8)&0x10))return false;
    SequenceOriginSchema<TargetSequenceSeekOps> fields(ops);
    const auto cls=ops.read<uint64_t>(player.address+16),ac=ops.read<uint64_t>(actor.address+16);
    if(!ops.is_class(cls) || !ops.is_class(ac) || !fields.named(cls,"LevelSequencePlayer","/Script/LevelSequence") ||
       !fields.named(ac,"LevelSequenceActor","/Script/LevelSequence") ||
       !fields.named(ops.read<uint64_t>(cls+0x40),"MovieSceneSequencePlayer","/Script/MovieScene") ||
       ops.read<uint64_t>(player.address+32)!=actor.address ||
       !fields.field(ac,"SequencePlayer","ObjectProperty",720,8,0x6e11d38,80501912059257404ULL) ||
       ops.read<uint64_t>(actor.address+720)!=player.address ||
       !SequenceSeekSchema<TargetSequenceSeekOps>(ops).function(p.function))return false;
    const auto dispatch=ops.read<uint64_t>(ops.read<uint64_t>(player.address)+0x268);
    // Qualified from GetStartTime/GetEndTime on the fingerprinted executable.
    return (dispatch==ops.base+0x1393330 || dispatch==ops.base+0x332bb90) &&
        sequence_seek_range(p,ops.read<int32_t>(player.address+0x298),ops.read<int32_t>(player.address+0x29c)) && ops.context();
}

// No C++ destructors cross SEH. The only FString in the engine parameter frame
// is locally zero-initialized. MarkedFrame mode and caller strings are forbidden.
inline uint32_t sequence_seek_execute(uint64_t base,const CallIdentity& player,const CallIdentity& actor,SequenceSeekPacket& p) {
    __try {
        TargetSequenceSeekOps ops{{base}};
        if(!sequence_seek_target(ops,player,actor,p))return 1691;
        alignas(16) uint8_t bytes[56]{};sequence_seek_parameters(p,bytes);
        const auto dispatch=ops.read<uint64_t>(ops.read<uint64_t>(player.address)+0x268);
        p.outcome=CallOutcomeUnknown;
        reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(dispatch)(reinterpret_cast<void*>(player.address),
            reinterpret_cast<void*>(p.function.address),bytes);
        if(!ops.context() || !ops.identity(player) || !ops.identity(actor) ||
           ops.read<uint64_t>(actor.address+720)!=player.address)return 1693;
        p.outcome=CallDispatchReturned;return 0;
    } __except(EXCEPTION_EXECUTE_HANDLER) {return p.outcome==CallNotDispatched ? 1691 : 1693;}
}
