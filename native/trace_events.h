#pragma once
#include "trace_copy.h"
#include <array>
#include <mutex>
#include <limits>

namespace e33_trace {
struct Ticket { uint64_t session = 0, registration = 0; };
struct Identity { uint32_t pid = 0; int32_t index = -1, serial = -1; };
struct Event {
    Ticket ticket;
    Identity object;
    uint64_t sequence = 0, monotonic_ms = 0;
    uint32_t thread = 0;
    Copy value{};
};
enum class State { unopened, active, stopped, expired, capped, closed };
struct QueueStatus { State state; uint32_t observed, queued, dropped; };

// Stable, one-registration owner. No pointers leave this queue. The surrounding
// slot must detach its callback before destruction. Never call slot operations
// while holding this queue's lock (native POST takes slot lock, then queue lock).
template<size_t Capacity = 64>
class Events {
    static_assert(Capacity > 0 && Capacity <= 1000);
    std::mutex lock_;
    std::array<Event, Capacity> events_{};
    Ticket ticket_{};
    uint64_t start_ = 0, deadline_ = 0;
    uint32_t thread_ = 0, limit_ = 0, observed_ = 0, dropped_ = 0;
    size_t head_ = 0, count_ = 0;
    State state_ = State::unopened;
    bool matches(Ticket ticket) const {
        return ticket.session && ticket.registration && ticket.session == ticket_.session &&
               ticket.registration == ticket_.registration;
    }
    void expire(uint64_t now) {
        if (state_ == State::active && now >= deadline_) state_ = State::expired;
    }
public:
    bool open(Ticket ticket, uint32_t thread, uint64_t now, uint32_t duration_ms, uint32_t limit) {
        std::lock_guard<std::mutex> guard(lock_);
        if (state_ != State::unopened || !ticket.session || !ticket.registration || !thread ||
            !duration_ms || duration_ms > 300000 || !limit || limit > 1000 ||
            now > std::numeric_limits<uint64_t>::max() - duration_ms) return false;
        ticket_ = ticket; thread_ = thread; start_ = now; deadline_ = now + duration_ms;
        limit_ = limit; state_ = State::active; return true;
    }
    bool offer(Ticket ticket, uint32_t thread, uint64_t now, Identity object, const Copy& value) {
        std::lock_guard<std::mutex> guard(lock_);
        if (!matches(ticket) || thread != thread_ || now < start_ || value.size > max_bytes ||
            !object.pid || object.index < 0 || object.serial < 0) return false;
        expire(now);
        if (state_ != State::active) return false;
        ++observed_;
        if (observed_ == limit_) state_ = State::capped;
        if (count_ == Capacity) { ++dropped_; return false; }
        auto& event = events_[(head_ + count_) % Capacity];
        event = {}; event.ticket = ticket_; event.object = object;
        event.sequence = observed_; event.monotonic_ms = now; event.thread = thread;
        event.value.size = value.size;
        std::memcpy(event.value.bytes, value.bytes, value.size);
        ++count_; return true;
    }
    bool pop(Ticket ticket, Event& event) {
        std::lock_guard<std::mutex> guard(lock_);
        event = {};
        if (!matches(ticket) || state_ == State::closed || !count_) return false;
        event = events_[head_]; events_[head_] = {};
        head_ = (head_ + 1) % Capacity; --count_; return true;
    }
    bool stop(Ticket ticket) {
        std::lock_guard<std::mutex> guard(lock_);
        if (!matches(ticket) || state_ == State::closed) return false;
        if (state_ == State::active) state_ = State::stopped;
        return true; // Preserve copied events for trace_read after trace_stop.
    }
    QueueStatus status(uint64_t now) {
        std::lock_guard<std::mutex> guard(lock_);
        expire(now);
        return {state_, observed_, static_cast<uint32_t>(count_), dropped_};
    }
    void close() {
        std::lock_guard<std::mutex> guard(lock_);
        state_ = State::closed; ticket_ = {}; count_ = head_ = 0;
        for (auto& event : events_) event = {};
    }
};
}
