#pragma once
#include "trace_slots.h"
#include "trace_events.h"

namespace e33_trace {
using Collector = bool (*)(void*, void*, void*, void*, Identity&, Copy&);
enum class Cleanup { attached, restored, conflict, storage_lost, wrong_thread };

// A nonmovable, one-registration owner. Explicit stop/close requires game-thread
// proof that the engine entry storage is still live. Destruction detaches only:
// no callback can reach freed context, but restoring the entry is a separate duty.
template<class Slots = TraceSlots<>, size_t QueueCapacity = 64>
class Registration {
    Events<QueueCapacity> queue_;
    Ticket ticket_{};
    uint32_t thread_{};
    size_t handle_{};
    Collector collector_{};
    void* context_{};
    Cleanup cleanup_ = Cleanup::restored;
    std::atomic<uint64_t> rejected_{0};
    static void post(void* context, void* object, void* frame, void* result) {
        auto& self = *static_cast<Registration*>(context);
        const auto thread = GetCurrentThreadId();
        if (thread != self.thread_) return;
        const auto now = GetTickCount64();
        if (self.queue_.status(now).state != State::active) return;
        Identity identity{}; Copy value{};
        // Production collectors must also guard target-memory SEH faults.
        bool accepted = false;
        try { accepted = self.collector_(self.context_, object, frame, result, identity, value); }
        catch (...) { accepted = false; }
        if (!accepted) { ++self.rejected_; return; }
        self.queue_.offer(self.ticket_, thread, now, identity, value);
    }
    Cleanup detach(bool storage_live) {
        if (!handle_) return cleanup_;
        if (!storage_live) {
            Slots::detach(handle_); cleanup_ = Cleanup::storage_lost;
        } else {
            cleanup_ = Slots::remove(handle_) ? Cleanup::restored : Cleanup::conflict;
        }
        handle_ = 0;
        return cleanup_;
    }
public:
    Registration() = default;
    Registration(const Registration&) = delete;
    Registration& operator=(const Registration&) = delete;
    ~Registration() {
        if (handle_) Slots::detach(handle_);
        queue_.close();
    }
    bool open(void* volatile* address, Entry expected, Ticket ticket, uint32_t thread,
              uint32_t duration_ms, uint32_t limit, Collector collector, void* context, bool before = false) {
        if (!collector || thread != GetCurrentThreadId() ||
            !queue_.open(ticket, thread, GetTickCount64(), duration_ms, limit)) return false;
        ticket_ = ticket; thread_ = thread; collector_ = collector; context_ = context;
        handle_ = before ? Slots::install(address, expected, post, this, true) : Slots::install(address, expected, post, this);
        if (!handle_) { queue_.close(); return false; }
        cleanup_ = Cleanup::attached;
        return true;
    }
    Cleanup stop(bool storage_live) {
        if (GetCurrentThreadId() != thread_) return Cleanup::wrong_thread;
        queue_.stop(ticket_);
        return detach(storage_live);
    }
    // Called by the game-thread scheduler even when no trace reads are requested.
    // Never called from post: the slot lock must not be acquired recursively.
    Cleanup maintain(bool storage_live, uint64_t now) {
        if (GetCurrentThreadId() != thread_) return Cleanup::wrong_thread;
        if (!storage_live) return stop(false);
        if (queue_.status(now).state != State::active) return detach(true);
        return cleanup_;
    }
    Cleanup close(bool storage_live) {
        const auto result = stop(storage_live);
        if (result != Cleanup::wrong_thread) queue_.close();
        return result;
    }
    bool pop(Ticket ticket, Event& event) { return queue_.pop(ticket, event); }
    bool renew(uint32_t duration_ms, uint32_t limit) {
        return GetCurrentThreadId() == thread_ && handle_ && cleanup_ == Cleanup::attached &&
            queue_.renew(ticket_, GetTickCount64(), duration_ms, limit);
    }
    QueueStatus status(uint64_t now) { return queue_.status(now); }
    uint64_t rejected() const { return rejected_.load(); }
    bool allows_entry(void* volatile* address, Entry expected, Entry current) const {
        return handle_ && Slots::matches(handle_, address, expected, current);
    }
};
}
