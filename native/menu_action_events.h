#pragma once
#include <cstddef>
#include <cstdint>
#include <limits>

// Game-thread-owned candidate core. No engine pointers cross into the controller.
// The adapter must validate thread/identity and capture a ticket BEFORE calling
// the original delegate. Completion revalidates that ticket AFTER the call,
// because the original can synchronously revoke or replace a registration.
struct MenuActionTicket {
    uint64_t session=0, registration=0, owner=0, action=0;
};
struct MenuActionEvent {
    MenuActionTicket ticket;
    uint64_t sequence=0;
};

template<size_t Registrations=64,size_t Capacity=64>
class MenuActionEvents {
    static_assert(Registrations>0 && Capacity>0);
    struct Route { uint64_t instance=0; MenuActionTicket ticket; };
    Route routes_[Registrations]{};
    MenuActionEvent events_[Capacity]{};
    uint64_t session_=0, generation_=0, sequence_=0, dropped_=0;
    size_t count_=0;

    static bool same(const MenuActionTicket& a,const MenuActionTicket& b) {
        return a.session==b.session && a.registration==b.registration &&
               a.owner==b.owner && a.action==b.action;
    }
    void erase_events(uint64_t registration) {
        size_t kept=0;
        for(size_t i=0;i<count_;++i)
            if(events_[i].ticket.registration!=registration) events_[kept++]=events_[i];
        for(size_t i=kept;i<count_;++i) events_[i]={};
        count_=kept;
    }
public:
    MenuActionEvents()=default;
    MenuActionEvents(const MenuActionEvents&)=delete;
    MenuActionEvents& operator=(const MenuActionEvents&)=delete;
    bool open(uint64_t session) {
        if(!session || session_) return false;
        session_=session;
        return true;
    }
    void close() {
        for(auto& route:routes_) route={};
        for(auto& event:events_) event={};
        session_=0; count_=0; dropped_=0;
        // Never reset generations, even if a controller reuses its session ID.
    }
    MenuActionTicket bind(uint64_t session,uint64_t owner,uint64_t action,uint64_t instance) {
        if(!session_ || session!=session_ || !owner || !action || !instance ||
           generation_==std::numeric_limits<uint64_t>::max()) return {};
        for(const auto& route:routes_) if(route.instance==instance) return {};
        for(auto& route:routes_) if(!route.instance) {
            route={instance,{session_,++generation_,owner,action}};
            return route.ticket;
        }
        return {};
    }
    MenuActionTicket begin(uint64_t instance) const {
        if(instance && session_)
            for(const auto& route:routes_) if(route.instance==instance) return route.ticket;
        return {};
    }
    bool finish(const MenuActionTicket& ticket) {
        if(!session_ || ticket.session!=session_ || !ticket.registration) return false;
        bool active=false;
        for(const auto& route:routes_)
            if(route.instance && same(route.ticket,ticket)) { active=true; break; }
        if(!active) return false;
        if(count_==Capacity || sequence_==std::numeric_limits<uint64_t>::max()) {
            if(dropped_!=std::numeric_limits<uint64_t>::max()) ++dropped_;
            return false;
        }
        events_[count_++]={ticket,++sequence_};
        return true;
    }
    bool revoke(const MenuActionTicket& ticket) {
        if(!session_ || ticket.session!=session_ || !ticket.registration) return false;
        for(auto& route:routes_) if(route.instance && same(route.ticket,ticket)) {
            route={}; erase_events(ticket.registration); return true;
        }
        return false;
    }
    void revoke_owner(uint64_t session,uint64_t owner) {
        if(!session_ || session!=session_ || !owner) return;
        for(auto& route:routes_) if(route.instance && route.ticket.owner==owner) {
            erase_events(route.ticket.registration); route={};
        }
    }
    bool pop(uint64_t session,MenuActionEvent& output) {
        output={};
        if(!session_ || session!=session_ || !count_) return false;
        output=events_[0];
        for(size_t i=1;i<count_;++i) events_[i-1]=events_[i];
        events_[--count_]={};
        return true;
    }
    uint64_t take_dropped(uint64_t session) {
        if(!session_ || session!=session_) return 0;
        auto result=dropped_; dropped_=0; return result;
    }
};
