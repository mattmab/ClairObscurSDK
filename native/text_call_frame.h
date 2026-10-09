#pragma once
#include "text_call_protocol.h"

enum class TextFrameState { Empty, Preparing, Ready, DispatchUnknown, Returned,
                            Copying, Copied, Cleaned, Published, Quarantined };
enum class TextFrameResult { Ok, BadState, BadPacket, ValueFailed, CleanupDeferred, Quarantined };

// Native-session storage, never stack-scoped around dispatch or sent over IPC.
// Each owner is either values[i] OR the corresponding argument slot, never both.
// A fault during dispatch leaves ownership in the durable argument buffer and
// forbids cleanup/retry; no guessed post-fault destructor call is permitted.
struct TextCallFrame {
    alignas(16) uint8_t arguments[kCallBytes]{};
    OwnedTextStorage values[kTextCallSlots];
    TextCallSlot results[kTextCallSlots]{};
    uint32_t offsets[kTextCallSlots]{}, count=0;
    TextFrameState state=TextFrameState::Empty;
    OwnedTextResult value_error=OwnedTextResult::Ok;
    bool copied=false;

    TextCallFrame()=default;
    TextCallFrame(const TextCallFrame&)=delete;
    TextCallFrame& operator=(const TextCallFrame&)=delete;

    bool available() const {
        if(state!=TextFrameState::Empty || count) return false;
        for(const auto& value:values) if(value.state!=OwnedTextState::Empty) return false;
        return true;
    }

    template<class Ops>
    TextFrameResult prepare(Ops& ops,const TextCallPacket& packet) {
        if(!available()) return TextFrameResult::BadState;
        if(validate_text_call(packet)) return TextFrameResult::BadPacket;
        // Caller first validates ALL target identities/property metadata and
        // initializes non-text argument bytes/object patches in arguments.
        count=packet.count;
        state=TextFrameState::Preparing;
        for(uint32_t i=0;i<count;++i) {
            const auto& input=packet.texts[i];
            const auto& field=packet.retained.call.fields[input.field_index];
            offsets[i]=field.offset;
            results[i].field_index=input.field_index;
            const uint16_t empty[1]{};
            // Initialize output FText too: the target getter performs move
            // assignment and may release the old result value.
            value_error=create_owned_text(ops,values[i],input.count ? input.units : empty,
                                           input.count ? input.count : 1);
            if(value_error!=OwnedTextResult::Ok) return TextFrameResult::ValueFailed;
        }
        state=TextFrameState::Ready;
        return TextFrameResult::Ok;
    }

    template<class Ops>
    TextFrameResult begin_dispatch(Ops& ops) {
        if(state!=TextFrameState::Ready) return TextFrameResult::BadState;
        if(!ops.can_create()) { value_error=OwnedTextResult::InvalidContext; return TextFrameResult::ValueFailed; }
        for(uint32_t i=0;i<count;++i) if(values[i].state!=OwnedTextState::Live || !ops.known_text(values[i].value)) {
            value_error=OwnedTextResult::UnsupportedValue; return TextFrameResult::ValueFailed;
        }
        // Transfer ownership before entering the engine. These are bounded
        // writes to session-owned storage, not engine operations.
        for(uint32_t i=0;i<count;++i) {
            std::memcpy(arguments+offsets[i],&values[i].value,16);
            values[i].value={}; values[i].state=OwnedTextState::Empty;
        }
        state=TextFrameState::DispatchUnknown;
        return TextFrameResult::Ok;
    }

    TextFrameResult dispatch_returned() {
        // Called only after the actual dispatcher returns normally, never by
        // fault recovery. Ref/out arguments may now own different text values.
        if(state!=TextFrameState::DispatchUnknown) return TextFrameResult::BadState;
        for(uint32_t i=0;i<count;++i) {
            std::memcpy(&values[i].value,arguments+offsets[i],16);
            values[i].state=OwnedTextState::Live;
            std::memset(arguments+offsets[i],0,16);
        }
        state=TextFrameState::Returned;
        return TextFrameResult::Ok;
    }

    template<class Ops>
    TextFrameResult copy_results(Ops& ops) {
        if(state!=TextFrameState::Returned) return TextFrameResult::BadState;
        state=TextFrameState::Copying;
        for(uint32_t i=0;i<count;++i) {
            value_error=copy_owned_text(ops,values[i],results[i].units,kOwnedTextUnits,results[i].count);
            if(value_error!=OwnedTextResult::Ok) return TextFrameResult::ValueFailed;
        }
        copied=true;
        state=TextFrameState::Copied;
        return TextFrameResult::Ok;
    }

    template<class Ops>
    TextFrameResult cleanup(Ops& ops) {
        if(state==TextFrameState::DispatchUnknown || state==TextFrameState::Quarantined)
            return TextFrameResult::Quarantined;
        if(state==TextFrameState::Empty || state==TextFrameState::Cleaned || state==TextFrameState::Published)
            return TextFrameResult::Ok;
        bool deferred=false, uncertain=false;
        for(uint32_t i=count;i>0;--i) {
            const auto result=release_owned_text(ops,values[i-1]);
            if(result==OwnedTextResult::ReleaseDeferred) deferred=true;
            else if(result!=OwnedTextResult::Ok) { uncertain=true; value_error=result; }
            // An SEH fault here leaves this record ReleaseUnknown. A later
            // cleanup may release other known owners but cannot retry this one.
        }
        if(uncertain) { state=TextFrameState::Quarantined; return TextFrameResult::Quarantined; }
        if(deferred) return TextFrameResult::CleanupDeferred;
        state=TextFrameState::Cleaned;
        return TextFrameResult::Ok;
    }

    TextFrameResult publish(TextCallPacket& packet) {
        if(state!=TextFrameState::Cleaned || !copied || packet.count!=count)
            return TextFrameResult::BadState;
        // Publish copied text only after every owned native value was released.
        // The caller still validates/captures object outputs and sets outcome.
        for(uint32_t i=0;i<count;++i) packet.texts[i]=results[i];
        state=TextFrameState::Published;
        return TextFrameResult::Ok;
    }

    bool reset() {
        if(state!=TextFrameState::Empty && state!=TextFrameState::Cleaned && state!=TextFrameState::Published)
            return false;
        for(const auto& value:values) if(value.state!=OwnedTextState::Empty) return false;
        std::memset(arguments,0,sizeof(arguments));
        for(auto& result:results) result={};
        for(auto& offset:offsets) offset=0;
        count=0; copied=false; value_error=OwnedTextResult::Ok; state=TextFrameState::Empty;
        return true;
    }
};
