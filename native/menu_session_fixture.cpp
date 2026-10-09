#include "menu_session.h"
#include <cstdio>
#include <stdexcept>
#include <string>
#include <vector>

static void check(bool value,const char* why) { if(!value) throw std::runtime_error(why); }
struct Ops {
    bool valid=true, registration=true, retained=false;
    bool throw_capture=false, throw_release=false;
    MenuResult capture_result=MenuResult::Ok, release_result=MenuResult::Ok;
    MenuContext current=MenuContext::Ready;
    std::vector<std::string> events;
    bool validate_preparation(uint64_t,uint64_t,uint64_t,uint64_t) { return valid; }
    bool validate_owned(uint64_t,uint64_t,uint64_t,uint64_t) { return registration; }
    MenuResult capture_baseline() {
        events.push_back("capture"); retained=true;
        if(throw_capture) throw std::runtime_error("capture interrupted");
        return capture_result;
    }
    MenuResult release_prepared_baseline() {
        events.push_back("release");
        if(throw_release) throw std::runtime_error("release interrupted");
        if(release_result==MenuResult::Ok) retained=false;
        return release_result;
    }
    MenuContext context() { return current; }
    bool prior_target_valid() { return true; }
    MenuFocusOwner focus_owner() { return MenuFocusOwner::Owned; }
    bool attach() { events.push_back("attach"); return true; }
    bool focus() { events.push_back("focus"); return true; }
    bool restore() { events.push_back("restore"); return true; }
    bool deactivate() { events.push_back("deactivate"); return true; }
    bool detach() { events.push_back("detach"); return true; }
    bool release_baseline() { return release_prepared_baseline()==MenuResult::Ok; }
};
using R=MenuResult;
int main() {
    {
        MenuSession m; Ops o; o.valid=false;
        check(m.prepare(o,1,2,3,4)==R::Invalid && !m.active() && o.events.empty(),"read-only rejection");
        o.valid=true; o.registration=false;
        check(m.prepare(o,1,2,3,4)==R::Invalid && !m.active() && !o.retained,"failed registration releases baseline");
        check(o.events==std::vector<std::string>({"capture","release"}),"no attachment on rejected registration");
        o.registration=true;
        check(m.prepare(o,1,2,3,4)==R::Ok,"reuse after fully cleaned failure");
        check(m.protects(1,3) && m.protects(1,4) && !m.protects(2,3),"session lease isolation");
        check(m.close(o,1,99)==R::Invalid && m.active(),"foreign close");
        check(m.attach(o,1,2)==R::Ok && m.focus(o,1,2)==R::Ok,"menu active");
        o.current=MenuContext::Deferred;
        check(m.close_session(o)==R::Deferred && m.protects(1,3),"deferred cleanup pins leases");
        o.current=MenuContext::Ready;
        check(m.close_session(o)==R::Ok && !m.active() && !o.retained,"close before pool release");
        auto events=o.events;
        check(m.close_session(o)==R::Ok && o.events==events,"empty close idempotent");
    }
    {
        MenuSession m; Ops o; o.registration=false; o.release_result=R::Deferred;
        check(m.prepare(o,1,2,3,4)==R::Deferred && m.active() && o.retained,"pre-registration deferred ownership");
        check(m.protects(1,3) && m.prepare(o,5,6,7,8)==R::Busy,"no adoption during preparation");
        o.release_result=R::Ok;
        check(m.close_session(o)==R::Ok && !m.active(),"resume baseline-only cleanup");
    }
    for(bool release_fault:{false,true}) {
        MenuSession m; Ops o;
        o.throw_capture=!release_fault; o.throw_release=release_fault; o.registration=false;
        try { m.prepare(o,1,2,3,4); } catch(const std::runtime_error&) { m.quarantine(); }
        auto events=o.events;
        check(m.active() && m.protects(1,3) && m.protects(1,4),"interrupted preparation retains lease protection");
        check(m.close_session(o)==R::Quarantined && o.events==events,"no replay after interruption");
        check(m.prepare(o,5,6,7,8)==R::Busy,"no new owner after uncertainty");
    }
    std::puts("Menu session: preparation ownership, rejected registration, deferred cleanup, owner isolation and interruption quarantine passed.");
}
