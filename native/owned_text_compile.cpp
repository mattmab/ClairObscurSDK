#define NOMINMAX
#include <Windows.h>
#include "target_owned_text.h"
#include "text_call_frame.h"
#include "target_text_call.h"

// Compile the actual target adapter/template path without calling into a game.
OwnedTextResult compile_owned_text(uint64_t base,OwnedTextStorage& storage,
                                   uint16_t* buffer,uint32_t capacity,uint32_t& count) {
    TargetOwnedTextOps ops{base};
    auto result=create_owned_text(ops,storage,buffer,capacity);
    if(result!=OwnedTextResult::Ok) return result;
    result=copy_owned_text(ops,storage,buffer,capacity,count);
    if(result!=OwnedTextResult::Ok) return result;
    return release_owned_text(ops,storage);
}

TextFrameResult compile_text_frame(uint64_t base,TextCallFrame& frame,TextCallPacket& packet) {
    TargetOwnedTextOps ops{base};
    auto result=frame.prepare(ops,packet);
    if(result!=TextFrameResult::Ok) return frame.cleanup(ops);
    result=frame.begin_dispatch(ops);
    if(result!=TextFrameResult::Ok) return frame.cleanup(ops);
    // Compile-only path. The real runtime must dispatch here and call the next
    // method only on a normal return, never on the SEH recovery path.
    result=frame.dispatch_returned();
    if(result!=TextFrameResult::Ok) return result;
    result=frame.copy_results(ops);
    auto cleanup=frame.cleanup(ops);
    if(result!=TextFrameResult::Ok) return result;
    if(cleanup!=TextFrameResult::Ok) return cleanup;
    return frame.publish(packet);
}

uint32_t compile_text_dispatch(TargetTextCall& context,const CallRetention& retention,
                               const CallPodValidation& pod) {
    const auto handling=context.handling();
    return reflected_call(context.base,context.packet->retained.call,&retention,&pod,&handling);
}
