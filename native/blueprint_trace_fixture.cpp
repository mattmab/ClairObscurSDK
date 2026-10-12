#define E33_BLUEPRINT_TRACE_SESSION
#include "blueprint_trace_frame.h"
#include "trace_plan.h"
#include "trace_slots.h"
#include <cassert>
#include <cstdio>

static int value = 0, before_value = -1;
static void __fastcall original(void*, void*, void*) { ++value; }
static void observe(void*, void*, void*, void*) { before_value = value; }
int main() {
    using namespace e33_trace;
    uint8_t bytes[0xa8]{};
    auto put = [&](unsigned at, uint64_t v) { std::memcpy(bytes + at, &v, 8); };
    put(0x10, 0x100); put(0x90, 0x100); put(0x18, 0x200);
    put(0x20, 0x300); put(0x28, 0x400);
    auto read = [&](uint64_t at, void* out, uint32_t size) {
        if (at < 0x1000 || at + size > 0x1000 + sizeof(bytes)) return false;
        std::memcpy(out, bytes + at - 0x1000, size); return true;
    };
    FrameStorage storage{};
    assert(resolve_blueprint_entry(read, 0x1000, 0x100, 0x200, 0x300, storage) == FrameError::none);
    assert(storage.locals == 0x400);
    put(0x90,0);
    assert(resolve_blueprint_entry(read,0x1000,0x100,0x200,0x300,storage,true)==FrameError::none);
    assert(resolve_blueprint_entry(read,0x1000,0x100,0x200,0x300,storage)==FrameError::function);
    put(0x90,0x100);
    assert(resolve_blueprint_entry(read,0x1000,0x100,0x200,0x300,storage,true)==FrameError::function);
    for (unsigned offset : {0x10, 0x90, 0x18, 0x20, 0x28, 0x80}) {
        uint64_t saved{}; std::memcpy(&saved, bytes + offset, 8);
        put(offset, offset == 0x28 ? 0 : 0xdead);
        assert(resolve_blueprint_entry(read, 0x1000, 0x100, 0x200, 0x300, storage) != FrameError::none);
        assert(!storage.locals); put(offset, saved);
    }
    assert(resolve_blueprint_entry(read, UINT64_MAX, 0x100, 0x200, 0x300, storage) != FrameError::none);
    CallPacket p{};
    p.version = 1; p.target = {1,0,0x10000}; p.function = {2,0,0x20000};
    p.function_flags = 0x0c020000; p.entry_rva = 0x13937a0;
    p.parameter_size = p.allocation_extent = 32; p.return_offset = 65535; p.field_count = 4;
    const char* names[] = {"TargetCharacter", "SourceCharacter", "ReceivedDamages", "BattleDamages"};
    for (unsigned i=0;i<4;++i) {
        auto& f=p.fields[i]; strcpy_s(f.name,names[i]); f.kind=i==2 ? CallDouble : CallObject;
        f.offset=i*8; f.width=8; f.dimension=1; f.flags=0x80;
        if(i!=2) f.constraint={3,0,0x30000};
    }
    uint64_t properties[]={1,2,3,4}; CapturePlan plan{};
    assert(make_capture_plan(p,properties,4,plan));
    assert(plan.blueprint && plan.extent==56 && plan.fields[2].destination_offset==32);
    p.fields[0].flags|=0x100; assert(!make_capture_plan(p,properties,4,plan)); p.fields[0].flags=0x80;
    p.entry_rva++; assert(!make_capture_plan(p,properties,4,plan));
    using Slots=TraceSlots<4,2>;
    void* volatile entry=reinterpret_cast<void*>(&original);
    auto handle=Slots::install(&entry,original,observe,nullptr,true); assert(handle);
    auto stale=reinterpret_cast<Entry>(entry); stale(nullptr,nullptr,nullptr);
    assert(before_value==0 && value==1);
    assert(Slots::remove(handle)); stale(nullptr,nullptr,nullptr);
    assert(before_value==0 && value==2);
    std::puts("Blueprint entry bounds, identity fields, PRE ordering and stale forwarding passed.");
}
