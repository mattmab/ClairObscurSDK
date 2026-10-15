#include "../native/menu_focus_controls.h"
#include "../native/menu_action_events.h"
#include <cassert>
#include <set>
struct Ops {
 std::set<uint64_t> refs;
 bool can_acquire(uint64_t w,uint64_t c){return w==c;}
 bool add_reference(uint64_t c){return refs.insert(c).second;}
 bool known_reference(uint64_t w,uint64_t c){return w==c&&refs.count(c)!=0;}
 bool can_release(){return true;}
 bool release_reference(uint64_t c){return refs.erase(c)==1;}
};
int main(){
 MenuFocusControls<64> focus;Ops ops;MenuActionEvents<64,64> events;assert(events.open(1));
 for(uint64_t i=1;i<=64;++i){assert(focus.retain(ops,i,i)==SlateReferenceResult::Ok);auto ticket=events.bind(1,1,i,i);assert(ticket.registration);assert(events.finish(ticket));}
 assert(focus.retain(ops,65,65)==SlateReferenceResult::Busy);assert(!events.bind(1,1,65,65).registration);
 for(uint64_t i=1;i<=64;++i){bool owned=false;assert(focus.observe(ops,i,i,owned)&&owned);MenuActionEvent event;assert(events.pop(1,event));assert(event.ticket.action==i);}
 assert(focus.release(ops)==SlateReferenceResult::Ok);assert(ops.refs.empty());events.close();assert(events.open(2));
 assert(focus.retain(ops,65,65)==SlateReferenceResult::Ok);assert(focus.release(ops)==SlateReferenceResult::Ok);
}
