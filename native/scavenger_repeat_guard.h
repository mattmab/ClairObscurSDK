#pragma once
#include <cstdint>
// Used by native SEH-finally wrapper and portable lifecycle fixtures. No engine
// calls or writes in its destructor; only explicit validated two-byte source restoration. Both originals are read before either write.
struct ScavengerRepeatGuard {
    uint8_t original=0,original_restore_audio=0;
    bool attempted=false,restored=false;
    template<class Ops> bool prepare(Ops& ops) {
        return !attempted && ops.valid() && ops.read(original,original_restore_audio) && original<=1 && original_restore_audio<=1;
    }
    template<class Ops> void apply(Ops& ops) {attempted=true;ops.write(1,1);}
    template<class Ops> bool restore(Ops& ops) {
        if(restored)return true;
        if(!attempted)return true;
        if(!ops.valid())return false;
        ops.write(original,original_restore_audio);restored=true;return true;
    }
};
