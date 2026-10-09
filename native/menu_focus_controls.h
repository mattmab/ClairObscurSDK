#pragma once
#include "owned_slate_reference.h"
#include <array>
#include <cstddef>

// Menu lifetime ownership, independent of callback registration. A removed
// callback may leave its control focused. Never release these identities until
// focus restoration and viewport detachment have completed.
template<size_t Capacity=16>
class MenuFocusControls {
    std::array<OwnedSlateReference,Capacity> references_{};
public:
    template<class Ops>
    SlateReferenceResult retain(Ops& ops,uint64_t widget,uint64_t controller) {
        for(const auto& r:references_) if(r.widget==widget && r.controller==controller) {
            return r.state==SlateReferenceState::Live && ops.known_reference(widget,controller)
                ? SlateReferenceResult::Ok : SlateReferenceResult::Quarantined;
        }
        for(auto& r:references_) if(r.state==SlateReferenceState::Empty)
            return retain_slate_reference(ops,r,widget,controller);
        return SlateReferenceResult::Busy;
    }
    template<class Ops>
    bool observe(Ops& ops,uint64_t widget,uint64_t controller,bool& owned) const {
        owned=false;
        for(const auto& r:references_) if(r.state!=SlateReferenceState::Empty) {
            if(r.state!=SlateReferenceState::Live || !ops.known_reference(r.widget,r.controller))
                return false;
            if(r.widget==widget && r.controller==controller) owned=true;
        }
        return true;
    }
    template<class Ops>
    SlateReferenceResult release(Ops& ops) {
        for(auto& r:references_) {
            auto result=release_slate_reference(ops,r);
            if(result!=SlateReferenceResult::Ok) return result;
        }
        return SlateReferenceResult::Ok;
    }
};
