#include "trace_events.h"
#include "trace_slots.h"
#include <cassert>
#include <cstdio>
#include <thread>

using namespace e33_trace;
static void __fastcall original(void*, void*, void* result) { *static_cast<uint8_t*>(result) = 73; }
struct Context { Events<4> queue; Ticket ticket{4, 5}; };
static void collect(void* context, void*, void*, void* result) {
    auto& ctx = *static_cast<Context*>(context);
    View views[] = {{static_cast<uint8_t*>(result), 1}};
    Field fields[] = {{0, 0, 0, 1}};
    Copy value{};
    assert(copy_fields(views, 1, fields, 1, 1, value) == CopyError::none);
    ctx.queue.offer(ctx.ticket, GetCurrentThreadId(), GetTickCount64(), {1, 2, 3}, value);
}
int main() {
    Events<2> queue;
    Ticket ticket{1, 2}; Identity object{3, 4, 5}; Copy value{};
    value.size = 1; value.bytes[0] = 9; value.bytes[1] = 255;
    assert(!queue.open(ticket, 7, UINT64_MAX, 1, 4));
    assert(queue.open(ticket, 7, 100, 100, 4));
    assert(!queue.open(ticket, 7, 100, 100, 4));
    assert(!queue.offer({1, 3}, 7, 101, object, value));
    assert(!queue.offer(ticket, 8, 101, object, value));
    assert(queue.offer(ticket, 7, 101, object, value));
    assert(queue.offer(ticket, 7, 102, object, value));
    assert(!queue.offer(ticket, 7, 103, object, value));
    auto state = queue.status(103);
    assert(state.observed == 3 && state.queued == 2 && state.dropped == 1);
    Event event;
    assert(!queue.pop({2, 2}, event));
    assert(queue.pop(ticket, event) && event.sequence == 1 && event.value.bytes[1] == 0);
    assert(queue.offer(ticket, 7, 104, object, value));
    assert(queue.status(104).state == State::capped);
    assert(!queue.offer(ticket, 7, 105, object, value));
    assert(queue.pop(ticket, event) && event.sequence == 2);
    assert(queue.pop(ticket, event) && event.sequence == 4); // Visible overflow gap.
    queue.close(); assert(!queue.pop(ticket, event));
    assert(!queue.open({3, 4}, 7, 106, 100, 4));
    Events<2> expiry;
    assert(expiry.open(ticket, 7, 100, 10, 3));
    assert(expiry.offer(ticket, 7, 109, object, value));
    assert(expiry.status(110).state == State::expired);
    assert(!expiry.offer(ticket, 7, 110, object, value));
    assert(expiry.pop(ticket, event));
    assert(!expiry.renew(ticket, 111, 100, 3)); // Expired work cannot be revived.
    Events<4> renewable;
    assert(renewable.open(ticket, 7, 100, 10, 2));
    assert(renewable.offer(ticket, 7, 101, object, value));
    assert(!renewable.renew({1,3}, 105, 100, 3));
    assert(renewable.renew(ticket, 105, 100, 3));
    assert(renewable.offer(ticket, 7, 120, object, value));
    assert(renewable.pop(ticket,event) && event.sequence==1);
    assert(renewable.pop(ticket,event) && event.sequence==2);
    assert(renewable.status(120).state==State::active);
    assert(renewable.stop(ticket));
    assert(!renewable.renew(ticket,121,100,3));
    // Exercise actual thunk -> independent copy -> bounded queue -> drain.
    Context ctx;
    assert(ctx.queue.open(ctx.ticket, GetCurrentThreadId(), GetTickCount64(), 10000, 10));
    alignas(8) void* volatile slot = reinterpret_cast<void*>(&original);
    using Pool = TraceSlots<2, 1>;
    auto handle = Pool::install(&slot, original, collect, &ctx); assert(handle);
    auto thunk = reinterpret_cast<Entry>(slot);
    uint8_t result = 0; thunk(nullptr, nullptr, &result);
    assert(result == 73 && ctx.queue.pop(ctx.ticket, event) && event.value.bytes[0] == 73);
    std::thread foreign([&] { uint8_t other = 0; thunk(nullptr, nullptr, &other); assert(other == 73); });
    foreign.join(); assert(!ctx.queue.pop(ctx.ticket, event));
    thunk(nullptr, nullptr, &result);
    assert(ctx.queue.stop(ctx.ticket));
    assert(Pool::remove(handle));
    assert(ctx.queue.pop(ctx.ticket, event)); // Stop retains already copied data.
    thunk(nullptr, nullptr, &result); assert(!ctx.queue.pop(ctx.ticket, event));
    ctx.queue.close();
    std::puts("Trace events: bounded overflow, sequence gaps, caps, expiry, tickets, stop retention and composed native delivery passed.");
}
