#pragma once
#include <cstdint>

// A separate, explicitly admitted mutation owner. TraceSlots remains strictly
// observational. The callee frame exists throughout begin/original/end; Build
// destroys it only after end returns. No callback runs under the trace lock.
namespace e33_blueprint_transform {
struct Decision {uint64_t token=0;bool skip=false;};
using Begin = Decision (*)(void*,uint64_t,void*,void*);
using End = void (*)(void*,uint64_t);
struct Slot {void* owner=nullptr;uint64_t function=0;Begin begin=nullptr;End end=nullptr;};
// Consumer-defined skills reserve execution/effect hooks alongside the existing
// story and encounter owners. All lookups and cleanup walk this bounded array.
inline Slot slots[64]{};
inline Slot find(uint64_t value){for(const auto&s:slots)if(s.owner&&s.function==value)return s;return {};}
inline bool selected(uint64_t value){return find(value).owner!=nullptr;}
inline bool attach(void* value,uint64_t target,Begin pre,End post){
 if(!value||!target||!pre||!post||selected(target))return false;
 for(auto&s:slots)if(!s.owner){s={value,target,pre,post};return true;}return false;
}
inline bool detach(void* value){
 bool found=false;for(auto&s:slots)if(s.owner==value){s={};found=true;}return found;
}
}
