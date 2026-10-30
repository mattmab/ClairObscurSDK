#pragma once
#include "sequence_origin_protocol.h"

namespace e33_sequence_origin {
enum class Result { ok, rejected, unknown };
// A single configuration attempt on a newly created owned actor. Ops supplies
// the exact build-specific schema/identity proof; a rejected proof never writes.
class Journal {
    enum State { fresh, configured, evaluated, uncertain } state_=fresh;
    bool owned_=false;
    SequenceOriginPacket last_{};
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
        last_=p;owned_=true;state_=configured; return Result::ok;
    }
    // The caller must establish that this exact player is idle on the game
    // thread. Re-prove the last acknowledged private value before each move;
    // never treat an evaluated but unconfigured player as an editable origin.
    template<class Ops> Result update(Ops& ops,const SequenceOriginPacket& p) {
        if(!owned_ || state_==uncertain || !sequence_origin_packet(p) || !ops.prove_private_current(last_))
            return Result::rejected;
        state_=uncertain;
        if(!ops.write_translation(p) || !ops.verify_translation(p))return Result::unknown;
        last_=p;state_=evaluated;return Result::ok;
    }
};

// Separate protocol and journal keep v1 translation acknowledgements intact.
// An update is permitted only after proving the exact last written transform.
class TransformJournal {
    enum State { fresh, configured, evaluated, uncertain } state_=fresh;
    bool owned_=false;
    SequenceOriginTransformPacket last_{};
public:
    bool before_evaluation() {
        if(state_==uncertain)return false;
        state_=evaluated;return true;
    }
    template<class Ops> Result configure(Ops& ops,const SequenceOriginTransformPacket& p) {
        if(state_!=fresh || !sequence_origin_transform_packet(p) || !ops.prove_private_fresh())return Result::rejected;
        state_=uncertain;
        if(!ops.write_transform(p) || !ops.verify_transform(p))return Result::unknown;
        last_=p;owned_=true;state_=configured;return Result::ok;
    }
    template<class Ops> Result update(Ops& ops,const SequenceOriginTransformPacket& p) {
        if(!owned_ || state_==uncertain || !sequence_origin_transform_packet(p) || !ops.prove_transform_current(last_))return Result::rejected;
        state_=uncertain;
        if(!ops.write_transform(p) || !ops.verify_transform(p))return Result::unknown;
        last_=p;state_=evaluated;return Result::ok;
    }
};
}
