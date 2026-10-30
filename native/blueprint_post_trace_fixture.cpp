#include <cstdint>
#include <cstring>
template<class T> T local_read(uint64_t address) {T value{};std::memcpy(&value,reinterpret_cast<const void*>(address),sizeof(value));return value;}
static bool target_trace_read(uint64_t address,void* out,size_t size) {std::memcpy(out,reinterpret_cast<const void*>(address),size);return true;}
#define E33_TRACE_ROUTING_FIXTURE
#include "blueprint_direct_trace.h"
#include <cassert>
using Slots=e33_trace::TraceSlots<>;
static unsigned originals=0,pre=0,post_count=0;
static size_t remove_during_original=0;
static bool replace_during_original=false;
static size_t replacement_handle=0;
static void* volatile* replacement_address=nullptr;
static void after(void*,void*,void*,void*);
struct Frame {uint8_t prefix[16]{};uint64_t function{};int value=1;};
static void __fastcall original(void*,void* frame,void* result) {
    assert(!blueprint_direct_frame);++originals;
    auto* f=static_cast<Frame*>(frame);f->value=42;*static_cast<int*>(result)=17;
    if(remove_during_original) {
        assert(Slots::remove(remove_during_original));remove_during_original=0;
        if(replace_during_original) {
            replacement_handle=Slots::install(replacement_address,original,after,nullptr,false,false);
            assert(replacement_handle);replace_during_original=false;
        }
    }
}
static void before(void*,void*,void* frame,void*) {assert(blueprint_direct_frame);assert(static_cast<Frame*>(frame)->value==1);++pre;}
static void after(void*,void*,void* frame,void* result) {assert(blueprint_direct_frame);assert(static_cast<Frame*>(frame)->value==42);assert(*static_cast<int*>(result)==17);++post_count;}
static void fault(void*,void*,void*,void*) {RaiseException(0xE0000001,0,0,nullptr);}
static void run(uint8_t* function) {
    Frame frame{};frame.function=reinterpret_cast<uint64_t>(function);int result=0;
    BlueprintDirectTrace::fixture_body(reinterpret_cast<uint64_t>(&original)-0x13938a0,nullptr,&frame,&result);
    assert(result==17 && frame.value==42 && !blueprint_direct_frame);
}
int main() {
    alignas(8) uint8_t function[256]{};auto* entry=reinterpret_cast<void* volatile*>(function+0xd8);
    *entry=reinterpret_cast<void*>(&original);
    auto handle=Slots::install(entry,original,before,nullptr,true,false);assert(handle);
    assert(*entry==reinterpret_cast<void*>(&original));run(function);assert(originals==1 && pre==1 && post_count==0);
    assert(Slots::remove(handle));
    handle=Slots::install(entry,original,after,nullptr,false,false);assert(handle);
    assert(Slots::observes_entry(entry));run(function);assert(originals==2 && pre==1 && post_count==1);
    remove_during_original=handle;run(function);assert(originals==3 && post_count==1);
    assert(!Slots::observes_entry(entry));
    handle=Slots::install(entry,original,fault,nullptr,false,false);assert(handle);
    run(function);assert(originals==4 && post_count==1 && !Slots::observes_entry(entry));
    assert(Slots::remove(handle));
    handle=Slots::install(entry,original,after,nullptr,false,false);assert(handle);
    run(function);assert(originals==5 && post_count==2);assert(Slots::remove(handle));
    run(function);assert(originals==6 && post_count==2);
    handle=Slots::install(entry,original,after,nullptr,false,false);assert(handle);
    replacement_address=entry;remove_during_original=handle;replace_during_original=true;
    run(function);assert(originals==7 && post_count==2); // New scope cannot inherit old call.
    run(function);assert(originals==8 && post_count==3);assert(Slots::remove(replacement_handle));
}

