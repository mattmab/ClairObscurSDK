#pragma once
#include "sequence_origin_protocol.h"

namespace e33_sequence_origin {
enum class Result { ok, rejected, unknown };
// A single configuration attempt on a newly created owned actor. Ops supplies
// the exact build-specific schema/identity proof; a rejected proof never writes.
class Journal {
    enum State { fresh, configured, evaluated, uncertain } state_=fresh;
public:
    bool quarantined() const {return state_==uncertain;}
    bool configured_origin() const {return state_==configured;}
    bool before_evaluation() {
        if(state_==uncertain) return false;
        state_=evaluated; return true;
    }
    template<class Ops> Result configure(Ops& ops,const SequenceOriginPacket& p) {
        if(state_!=fresh || !sequence_origin_packet(p) || !ops.prove_private_fresh())
            return Result::rejected;
        // Publish before the first write. Neither a fault nor a changed identity
        // permits replay, Play, or release of potentially used private storage.
        state_=uncertain;
        if(!ops.write_translation(p) || !ops.verify_translation(p)) return Result::unknown;
        state_=configured; return Result::ok;
    }
};
}
