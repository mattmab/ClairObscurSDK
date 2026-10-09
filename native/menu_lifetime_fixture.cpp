#include "menu_lifetime.h"
#include <cstdio>
#include <stdexcept>
#include <string>
#include <vector>

static void check(bool ok,const char* message) { if(!ok) throw std::runtime_error(message); }
struct Engine {
    MenuContext current=MenuContext::Ready;
    MenuFocusOwner focused=MenuFocusOwner::Owned;
    bool prior=true, valid=true;
    std::string fault, reject, defer_after;
    std::vector<std::string> events;
    MenuContext context() const { return current; }
    bool validate_owned(uint64_t,uint64_t,uint64_t,uint64_t) const { return valid; }
    bool prior_target_valid() const { return prior; }
    MenuFocusOwner focus_owner() const { return focused; }
    bool call(const char* name) {
        events.emplace_back(name);
        if(fault==name) throw std::runtime_error("interrupted engine call");
        if(reject==name) return false;
        if(defer_after==name) current=MenuContext::Deferred;
        return true;
    }
    bool attach() { return call("attach"); }
    bool focus() { return call("focus"); }
    bool restore() { if(!call("restore")) return false; focused=MenuFocusOwner::Prior; return true; }
    bool deactivate() { return call("deactivate"); }
    bool detach() { return call("detach"); }
    bool release_baseline() { return call("release"); }
};
using R=MenuResult;
static void prepare(MenuLifetime& menu,Engine& engine) {
    check(menu.register_owned(engine,10,20,30,40)==R::Ok,"register owned leases");
    check(menu.attach(engine,10,20)==R::Ok,"attach");
    check(menu.focus(engine,10,20)==R::Ok,"focus");
}
int main() {
    {
        Engine e; MenuLifetime m;
        check(m.register_owned(e,0,20,30,40)==R::Invalid,"zero session");
        check(m.register_owned(e,10,20,30,30)==R::Invalid,"duplicate lease");
        e.valid=false;
        check(m.register_owned(e,10,20,30,40)==R::Invalid && !m.active(),"foreign lease");
        e.valid=true; prepare(m,e);
        check(m.protects(10,30) && m.protects(10,40) && !m.protects(11,30),"lease protection");
        auto before=e.events;
        check(m.close(e,11,20)==R::Invalid && m.close(e,10,21)==R::Invalid,"owner isolation");
        check(e.events==before,"foreign close has no effects");
        check(m.close(e,10,20)==R::Ok && !m.active(),"normal close");
        check(e.events==std::vector<std::string>({"attach","focus","restore","deactivate","detach","release"}),"cleanup ordering");
        check(!m.protects(10,30),"leases releasable only after detach");
        before=e.events;
        check(m.close(e,10,20)==R::Invalid && e.events==before,"stale close does not replay");
    }
    for(auto who:{MenuFocusOwner::Prior,MenuFocusOwner::Unrelated}) {
        Engine e; MenuLifetime m; prepare(m,e); e.focused=who;
        check(m.close(e,10,20)==R::Ok,"nonowned focus close");
        check(e.events==std::vector<std::string>({"attach","focus","deactivate","detach","release"}),"do not steal focus");
    }
    for(const auto* stage:{"restore","deactivate","detach"}) {
        Engine e; MenuLifetime m; prepare(m,e); e.defer_after=stage;
        check(m.close(e,10,20)==R::Deferred && m.protects(10,30),"deferred keeps leases");
        e.current=MenuContext::Ready; e.defer_after.clear();
        check(m.close(e,10,20)==R::Ok,"resume cleanup");
        check(e.events==std::vector<std::string>({"attach","focus","restore","deactivate","detach","release"}),"resume does not repeat completed steps");
    }
    {
        Engine e; MenuLifetime m; prepare(m,e); e.current=MenuContext::Deferred;
        check(m.close(e,10,20)==R::Deferred && e.events.size()==2,"defer before any cleanup");
        e.focused=MenuFocusOwner::Unrelated; e.current=MenuContext::Ready;
        check(m.close(e,10,20)==R::Ok,"resume after external focus change");
        check(e.events==std::vector<std::string>({"attach","focus","deactivate","detach","release"}),"deferred cleanup preserves new focus owner");
    }
    {
        Engine e; MenuLifetime m;
        check(m.register_owned(e,10,20,30,40)==R::Ok,"activation-only registration");
        check(m.attach(e,10,20)==R::Ok,"activation-only attach");
        check(m.close(e,10,20)==R::Ok,"activation can take focus without explicit focus call");
        check(e.events==std::vector<std::string>({"attach","restore","deactivate","detach","release"}),"restore attachment-acquired focus");
    }
    for(const auto* stage:{"attach","focus","restore","deactivate","detach","release"}) {
        Engine e; MenuLifetime m;
        check(m.register_owned(e,10,20,30,40)==R::Ok,"fault registration");
        e.fault=stage;
        try {
            m.attach(e,10,20); m.focus(e,10,20); m.close(e,10,20);
        } catch(const std::runtime_error&) {}
        auto before=e.events;
        check(m.close(e,10,20)==R::Quarantined && e.events==before,"interrupted mutation never replayed");
        check(m.protects(10,30) && m.protects(10,40),"unknown ownership retained");
        check(m.register_owned(e,50,60,70,80)==R::Busy,"quarantine forbids reuse");
    }
    {
        Engine e; MenuLifetime m; prepare(m,e); e.prior=false;
        check(m.close(e,10,20)==R::Quarantined && e.events.size()==2,"stale prior target blocks restore");
    }
    {
        Engine e; MenuLifetime m; prepare(m,e); e.current=MenuContext::Terminal;
        check(m.close(e,10,20)==R::Quarantined && e.events.size()==2,"terminal teardown invokes no engine calls");
    }
    {
        Engine e; MenuLifetime m;
        check(m.register_owned(e,10,20,30,40)==R::Ok,"register before attachment");
        check(m.close(e,10,20)==R::Ok && e.events==std::vector<std::string>({"release"}),"never attached releases only captured baseline");
    }
    for(const auto* stage:{"attach","focus","restore","deactivate","detach","release"}) {
        Engine e; MenuLifetime m; e.reject=stage;
        check(m.register_owned(e,10,20,30,40)==R::Ok,"rejection registration");
        auto result=m.attach(e,10,20);
        if(result==R::Ok) result=m.focus(e,10,20);
        if(result==R::Ok) result=m.close(e,10,20);
        check(result==R::Quarantined && m.protects(10,40),"failed mutation verification keeps ownership");
        auto before=e.events;
        check(m.close(e,10,20)==R::Quarantined && e.events==before,"verification failure never replays");
    }
    std::puts("Menu lifetime: ordered cleanup, owner isolation, focus preservation, deferral and interrupted-call quarantine passed.");
}
