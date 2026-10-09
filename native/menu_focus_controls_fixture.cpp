#include "menu_focus_controls.h"
#include <cstdio>
#include <stdexcept>

static void check(bool ok,const char* message) { if(!ok) throw std::runtime_error(message); }
struct References {
    int counts[3]{1,1,1}, acquisitions=0, releases=0;
    bool ready=true, known=true, fault=false;
    bool known_reference(uint64_t w,uint64_t c) const {
        return known && c>=1 && c<=3 && w==c+16 && counts[c-1]>0;
    }
    bool can_acquire(uint64_t w,uint64_t c) const { return ready && known_reference(w,c); }
    bool can_release() const { return ready; }
    bool add_reference(uint64_t c) {
        ++counts[c-1]; ++acquisitions;
        if(fault) throw std::runtime_error("interrupted acquire");
        return true;
    }
    bool release_reference(uint64_t c) { --counts[c-1]; ++releases; return true; }
};
int main() {
    using R=SlateReferenceResult;
    References refs; MenuFocusControls<2> controls; bool owned=false;
    check(controls.retain(refs,17,1)==R::Ok && controls.retain(refs,18,2)==R::Ok,"capture both controls");
    check(controls.retain(refs,18,2)==R::Ok && refs.acquisitions==2,"deduplicate independent owner");
    check(controls.retain(refs,19,3)==R::Busy && refs.acquisitions==2,"capacity refuses acquisition");
    --refs.counts[1]; // Original owner/callback adapter relinquishes its reference.
    check(controls.observe(refs,18,2,owned) && owned,"second control survives callback owner removal");
    check(controls.observe(refs,19,3,owned) && !owned,"unrelated focus is not owned");
    check(controls.observe(refs,18,1,owned) && !owned,"both widget and controller must match");
    refs.ready=false;
    check(controls.release(refs)==R::Deferred && refs.releases==0,"deferred cleanup retains identities");
    refs.ready=true;
    check(controls.release(refs)==R::Ok && refs.releases==2 && refs.counts[1]==0,"release after detach exactly once");
    check(controls.release(refs)==R::Ok && refs.releases==2,"idempotent empty close");
    check(controls.observe(refs,18,2,owned) && !owned,"closed ownership cannot match stale focus");
    References bad; MenuFocusControls<2> unknown; bad.fault=true;
    try { unknown.retain(bad,17,1); } catch(const std::runtime_error&) {}
    check(!unknown.observe(bad,17,1,owned),"unknown acquisition cannot classify focus");
    check(unknown.release(bad)==R::Quarantined && bad.releases==0,"never replay unknown acquisition");
    std::puts("Menu control focus retention, selective callback independence, unrelated focus and quarantine passed.");
}
