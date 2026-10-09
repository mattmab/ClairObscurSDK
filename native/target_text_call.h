#pragma once
#include "target_owned_text.h"
#include "reflected_invocation.h"
#include "text_call_frame.h"

// Candidate context kept in durable native-session storage by the opt-in v12
// backend. Cleanup runs on every failure path; ambiguous ownership is preserved
// in the pinned module and prevents reuse after dispatch/SEH faults.
struct TargetTextCall {
    uint64_t base=0;
    TextCallPacket* packet=nullptr;
    TextCallFrame frame;
    static bool available(void* opaque) {
        return static_cast<TargetTextCall*>(opaque)->frame.available();
    }
    static uint32_t error(TextFrameResult result) {
        return result==TextFrameResult::Ok ? 0 : 700+static_cast<uint32_t>(result);
    }
    static uint32_t prepare(void* opaque) {
        auto& self=*static_cast<TargetTextCall*>(opaque);
        TargetOwnedTextOps ops{self.base};
        return error(self.frame.prepare(ops,*self.packet));
    }
    static uint32_t begin(void* opaque) {
        auto& self=*static_cast<TargetTextCall*>(opaque);
        TargetOwnedTextOps ops{self.base};
        return error(self.frame.begin_dispatch(ops));
    }
    static uint32_t returned(void* opaque) {
        return error(static_cast<TargetTextCall*>(opaque)->frame.dispatch_returned());
    }
    static uint32_t finish(void* opaque) {
        auto& self=*static_cast<TargetTextCall*>(opaque);
        TargetOwnedTextOps ops{self.base};
        const auto copied=self.frame.copy_results(ops);
        const auto cleaned=self.frame.cleanup(ops);
        if(copied!=TextFrameResult::Ok) return error(copied);
        if(cleaned!=TextFrameResult::Ok) return error(cleaned);
        return error(self.frame.publish(*self.packet));
    }
    CallTextHandling handling() {
        return {packet,frame.arguments,this,available,prepare,begin,returned,finish};
    }
};
