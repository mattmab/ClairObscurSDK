#pragma once
#include "target_slate_reference.h"

// Candidate capture only. No callback interception or event delivery. The caller
// must hold a verified UButton lease, run on the game thread, contain SEH, and
// revoke any future event adapter before releasing this retained Slate owner.
struct TargetButtonReference {
    CallIdentity button{-1,0,0};
    OwnedSlateReference slate;
    uint64_t delegate=0;

    static bool observe(uint64_t base,const CallIdentity& identity,
                        uint64_t& widget,uint64_t& controller,uint64_t& instance) {
        TargetButtonReferenceOps refs{base};
        if(!refs.can_release() || !call_identity(base,identity)) return false;
        auto object=identity.address;
        auto cls=local_read<uint64_t>(object+0x10);
        if(!call_is_class(base,cls) || !exact_name(base,cls+0x18,"Button") ||
           !exact_name(base,local_read<uint64_t>(cls+0x20)+0x18,"/Script/UMG") ||
           (local_read<uint32_t>(object+8)&(0x10|0x40000000))) return false;
        widget=local_read<uint64_t>(object+0x5f8);
        controller=local_read<uint64_t>(object+0x600);
        if(!refs.known_reference(widget,controller)) return false;
        instance=local_read<uint64_t>(widget+0x2d8);
        if(!instance || local_read<int32_t>(widget+0x2e0)!=3 ||
           local_read<uint64_t>(instance)!=base+0x7382098 ||
           local_read<int32_t>(instance+0x18)!=identity.index ||
           local_read<int32_t>(instance+0x1c)!=identity.serial ||
           local_read<uint64_t>(instance+0x20)!=base+0x3089290 ||
           local_read<int32_t>(instance+0x28)!=0) return false;
        return true;
    }
    SlateReferenceResult capture(uint64_t base,const CallIdentity& identity) {
        if(slate.state!=SlateReferenceState::Empty) return SlateReferenceResult::Busy;
        uint64_t widget=0, controller=0, instance=0;
        if(!observe(base,identity,widget,controller,instance)) return SlateReferenceResult::Invalid;
        button=identity; delegate=instance;
        TargetButtonReferenceOps refs{base};
        return retain_slate_reference(refs,slate,widget,controller);
    }
    bool unchanged(uint64_t base) const {
        if(slate.state!=SlateReferenceState::Live) return false;
        uint64_t widget=0, controller=0, instance=0;
        return observe(base,button,widget,controller,instance) &&
            widget==slate.widget && controller==slate.controller && instance==delegate;
    }
    SlateReferenceResult release(uint64_t base) {
        TargetButtonReferenceOps refs{base};
        auto result=release_slate_reference(refs,slate);
        if(result==SlateReferenceResult::Ok) { button={-1,0,0}; delegate=0; }
        return result;
    }
};
