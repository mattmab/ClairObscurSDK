#include "trace_slots.h"
#include <cassert>

using Pool=e33_trace::TraceSlots<8,2>;
static unsigned calls=0,observations=0;
static void __fastcall original(void*,void*,void*){++calls;}
static void __fastcall foreign(void*,void*,void*){}
static void observe(void*,void*,void*,void*){++observations;}
int main(){
    alignas(8) void* volatile entry=reinterpret_cast<void*>(&original);
    const auto post_registration=Pool::install(&entry,original,observe,nullptr,false,false);
    assert(post_registration&&entry==reinterpret_cast<void*>(&original));
    assert(Pool::remove(post_registration));
    const auto registration=Pool::install(&entry,original,observe,nullptr,true,false);
    assert(registration&&entry==reinterpret_cast<void*>(&original));
    assert(Pool::observes_entry(&entry));
    assert(!Pool::install(&entry,original,observe,nullptr,true,false));
    reinterpret_cast<e33_trace::Entry>(entry)(nullptr,nullptr,nullptr);
    assert(calls==1&&observations==0); // ordinary typed call entry stays original
    Pool::observe_entry(&entry,nullptr,nullptr,nullptr);
    assert(observations==1);
    assert(Pool::remove(registration));
    assert(entry==reinterpret_cast<void*>(&original)&&!Pool::observes_entry(&entry));
    Pool::observe_entry(&entry,nullptr,nullptr,nullptr);
    assert(observations==1);
    const auto second=Pool::install(&entry,original,observe,nullptr,true,false);
    entry=reinterpret_cast<void*>(&foreign);
    assert(!Pool::remove(second));
    assert(entry==reinterpret_cast<void*>(&foreign)&&!Pool::observes_entry(&entry));
    return 0;
}
