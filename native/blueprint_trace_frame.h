#pragma once
#include "trace_frame.h"

namespace e33_trace {
// PRE-only frame, before 1413937a0 runs. Do not accept advanced code cursors,
// alternate context adjustments, return storage, or external out chains.
template<class Reader>
FrameError resolve_blueprint_entry(Reader&& reader, uint64_t frame, uint64_t function,
                                  uint64_t object, uint64_t script, FrameStorage& output, bool direct = false) {
    output = {};
    if (!frame || frame > UINT64_MAX - 0x98 || !function || !object || !script)
        return FrameError::function;
    uint64_t initial{}, current{}, context{}, code{}, locals{}, out{};
    if (!reader(frame + 0x10, &initial, 8) || !reader(frame + 0x90, &current, 8) ||
        !reader(frame + 0x18, &context, 8) || !reader(frame + 0x20, &code, 8) ||
        !reader(frame + 0x28, &locals, 8) || !reader(frame + 0x80, &out, 8)) return FrameError::read;
    if (initial != function || current != (direct ? 0 : function) || context != object) return FrameError::function;
    if (code != script) return FrameError::bytecode;
    if (!locals || out) return FrameError::chain;
    output.locals = locals;
    return FrameError::none;
}
}
