#include "target_text_call.h"
#include <memory>
#include <iostream>

int main() {
    auto packet=std::make_unique<TextCallPacket>();
    packet->retained.call.version=kTextCallVersion;
    auto context=std::make_unique<TargetTextCall>();
    context->packet=packet.get();
    auto handling=context->handling();
    CallPodValidation pod{[](uint64_t,uint64_t,PodValueKind,const CallIdentity&) { return false; }};
    CallRetention retention{nullptr,[](void*,const CallPacket&) -> uint32_t { return 0; },
                            [](void*,uint32_t,CallIdentity&) -> uint32_t { return 0; }};
    // Every call must reject before consulting base0 or entering any engine code.
    if(reflected_call(0,packet->retained.call,nullptr,&pod)!=300) return 1;
    if(reflected_call(0,packet->retained.call,nullptr,&pod,&handling)!=227) return 2;
    if(reflected_call(0,packet->retained.call,&retention,nullptr,&handling)!=227) return 3;
    context->frame.state=TextFrameState::DispatchUnknown;
    context->frame.arguments[0]=42;
    if(reflected_call(0,packet->retained.call,&retention,&pod,&handling)!=230 ||
       context->frame.arguments[0]!=42 || context->frame.state!=TextFrameState::DispatchUnknown) return 4;
    context->frame.state=TextFrameState::Empty;
    context->frame.values[0].state=OwnedTextState::ReleaseUnknown;
    if(reflected_call(0,packet->retained.call,&retention,&pod,&handling)!=230) return 5;
    context->frame.values[0].state=OwnedTextState::Empty;
    if(reflected_call(0,packet->retained.call,&retention,&pod,&handling)!=600) return 6;
    handling.prepare=nullptr;
    if(reflected_call(0,packet->retained.call,&retention,&pod,&handling)!=227) return 7;
    std::cout << "Seven actual-dispatcher capability/quarantine gates passed without engine memory access.\n";
}
