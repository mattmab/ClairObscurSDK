#include "owned_slate_reference.h"
#include <cstdio>
#include <stdexcept>

static void check(bool ok,const char* message) { if(!ok) throw std::runtime_error(message); }
struct Engine {
    int strong=1, additions=0, releases=0, destructions=0;
    bool ready=true, known=true, acquire_fault=false, release_fault=false;
    bool can_acquire(uint64_t widget,uint64_t control) const { return ready && known && widget==116 && control==100 && strong>0; }
    bool can_release() const { return ready; }
    bool known_reference(uint64_t widget,uint64_t control) const { return known && widget==116 && control==100 && strong>0; }
    bool add_reference(uint64_t) {
        ++additions; ++strong;
        if(acquire_fault) throw std::runtime_error("acquire interrupted after increment");
        return true;
    }
    bool release_reference(uint64_t) {
        ++releases; --strong;
        if(release_fault) throw std::runtime_error("release interrupted after decrement");
        if(!strong) ++destructions;
        return true;
    }
};
int main() {
    using R=SlateReferenceResult;
    {
        Engine e; OwnedSlateReference r;
        check(retain_slate_reference(e,r,117,100)==R::Invalid && !e.additions,"reject unsupported target");
        check(retain_slate_reference(e,r,116,100)==R::Ok && e.strong==2,"own independent reference");
        check(retain_slate_reference(e,r,116,100)==R::Busy && e.strong==2,"no duplicate acquire");
        --e.strong; // Engine relinquishes its own reference while menu owns focus.
        check(e.strong==1 && !e.destructions,"retention survives original owner removal");
        e.ready=false;
        check(release_slate_reference(e,r)==R::Deferred && e.strong==1,"deferred release keeps reference");
        e.ready=true;
        check(release_slate_reference(e,r)==R::Ok && e.strong==0 && e.destructions==1,"release final owner exactly once");
        check(release_slate_reference(e,r)==R::Ok && e.releases==1,"empty release idempotent");
    }
    for(bool acquisition:{false,true}) {
        Engine e; OwnedSlateReference r;
        e.acquire_fault=acquisition;
        try {
            retain_slate_reference(e,r,116,100);
            e.release_fault=true;
            release_slate_reference(e,r);
        } catch(const std::runtime_error&) {}
        auto additions=e.additions, releases=e.releases, count=e.strong;
        check(release_slate_reference(e,r)==R::Quarantined,"unknown operation quarantines");
        check(e.additions==additions && e.releases==releases && e.strong==count,"never replay unknown reference operation");
        check(retain_slate_reference(e,r,116,100)==R::Busy,"quarantine forbids reuse");
    }
    {
        Engine e; OwnedSlateReference r;
        retain_slate_reference(e,r,116,100); e.known=false;
        check(release_slate_reference(e,r)==R::Quarantined && e.releases==0,"foreign controller forbids destruction");
    }
    std::puts("Slate reference: independent retention, final release, deferral and interrupted-operation quarantine passed.");
}
