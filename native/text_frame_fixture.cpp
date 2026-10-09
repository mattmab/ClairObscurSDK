#include "text_call_frame.h"
#include "owned_text_fixture_ops.h"
#include <iostream>
#include <memory>
#include <cstdlib>

static void specimen(TextCallPacket& p) {
    p={};
    auto& call=p.retained.call;
    call.version=3; call.parameter_size=call.allocation_extent=32; call.return_offset=16;
    call.target={1,2,0x1234}; call.function={3,4,0x5678}; call.field_count=2;
    call.fields[0]={kTextCallKind,0,16,1,0x80,0,"Input",{-1,0,0}};
    call.fields[1]={kTextCallKind,16,16,1,0x480,0,"ReturnValue",{-1,0,0}};
    p.count=2; p.texts[0].count=2; p.texts[0].units[0]='A'; p.texts[1].field_index=1;
}

int main() {
    unsigned checks=0;
    auto check=[&](bool condition) {
        ++checks; if(!condition) { std::cerr << "Frame check " << checks << " failed\n"; std::exit(1); }
    };
    using R=TextFrameResult;
    auto packet=std::make_unique<TextCallPacket>(); specimen(*packet);
    auto frame=std::make_unique<TextCallFrame>();
    FakeTextOps ops;
    check(frame->prepare(ops,*packet)==R::Ok && ops.values.size()==2);
    check(frame->publish(*packet)==R::BadState && !packet->texts[1].count);
    check(frame->prepare(ops,*packet)==R::BadState && ops.constructions==2);
    check(frame->begin_dispatch(ops)==R::Ok);
    check(frame->values[0].state==OwnedTextState::Empty && frame->values[1].state==OwnedTextState::Empty);
    check(frame->cleanup(ops)==R::Quarantined && ops.releases==0 && !frame->reset());
    // Simulate a normally returning engine function replacing its output FText.
    TargetTextValue output{}; std::memcpy(&output,frame->arguments+16,16);
    ops.release(output);
    uint16_t result[]{'B',0xd83d,0xde80,0};
    TargetStringValue source{reinterpret_cast<uint64_t>(result),4,4};
    ops.construct(output,source); std::memcpy(frame->arguments+16,&output,16);
    check(frame->dispatch_returned()==R::Ok);
    bool scrubbed=true; for(unsigned i=0;i<32;++i) scrubbed=scrubbed && !frame->arguments[i];
    check(scrubbed && frame->copy_results(ops)==R::Ok);
    check(frame->publish(*packet)==R::BadState);
    ops.context=false;
    check(frame->cleanup(ops)==R::CleanupDeferred && ops.values.size()==2);
    ops.context=true;
    check(frame->cleanup(ops)==R::Ok && ops.values.empty() && ops.releases==3);
    check(frame->cleanup(ops)==R::Ok && ops.releases==3);
    check(frame->publish(*packet)==R::Ok && packet->texts[1].count==4 && packet->texts[1].units[0]=='B');
    check(frame->publish(*packet)==R::BadState && frame->reset());

    // Rejection before materialization must acquire no ownership.
    specimen(*packet); packet->texts[0].count=0;
    check(frame->prepare(ops,*packet)==R::BadPacket && ops.values.empty());
    specimen(*packet); ops.context=false;
    check(frame->prepare(ops,*packet)==R::ValueFailed && ops.values.empty());
    ops.context=true; check(frame->cleanup(ops)==R::Ok && frame->reset());

    // Partial construction fault: known earlier allocations can be released;
    // the uncertain constructor is never retried or guessed to be unallocated.
    {
        FakeTextOps fault; fault.fail_construct_at=2;
        auto owned=std::make_unique<TextCallFrame>();
        bool caught=false;
        try { owned->prepare(fault,*packet); } catch(const std::runtime_error&) { caught=true; }
        check(caught && fault.values.size()==2);
        check(owned->cleanup(fault)==R::Quarantined && fault.releases==1 && fault.values.size()==1);
        check(owned->cleanup(fault)==R::Quarantined && fault.releases==1 && !owned->reset());
        check(owned->begin_dispatch(fault)==R::BadState && owned->publish(*packet)==R::BadState);
    }
    for(int phase=0;phase<3;++phase) {
        FakeTextOps fault; auto owned=std::make_unique<TextCallFrame>();
        check(owned->prepare(fault,*packet)==R::Ok && owned->begin_dispatch(fault)==R::Ok);
        if(phase==0) {
            // A dispatcher fault never calls dispatch_returned. No destructor
            // can safely infer what happened to input/ref/output allocations.
            check(owned->cleanup(fault)==R::Quarantined && fault.releases==0 && !owned->reset());
            continue;
        }
        check(owned->dispatch_returned()==R::Ok);
        bool caught=false;
        if(phase==1) {
            fault.fail_read=true;
            try { owned->copy_results(fault); } catch(const std::runtime_error&) { caught=true; }
        } else {
            check(owned->copy_results(fault)==R::Ok);
            fault.fail_release_at=1;
            try { owned->cleanup(fault); } catch(const std::runtime_error&) { caught=true; }
        }
        check(caught && owned->cleanup(fault)==R::Quarantined);
        const auto released=fault.releases;
        check(owned->cleanup(fault)==R::Quarantined && fault.releases==released && !owned->reset());
        check(owned->publish(*packet)==R::BadState);
    }
    std::cout << checks << " durable text-frame ownership/dispatch/publication/fault checks passed.\n";
}
