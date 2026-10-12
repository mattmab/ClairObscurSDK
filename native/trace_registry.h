#pragma once
#include "trace_protocol.h"
#include "trace_registration.h"
#include <memory>
#include <new>

namespace e33_trace {
enum class Storage { ready, deferred, lost };

// Ops supplies build-specific schema/identity checks. Entries own their context
// before the Registration member, so callbacks detach before context destruction.
template<class Ops, class Slots = TraceSlots<>>
class Registry {
    struct Item {
        uint64_t owner{}, id{};
        typename Ops::Context context{};
        Registration<Slots> registration;
        Cleanup cleanup = Cleanup::attached;
    };
    std::array<std::unique_ptr<Item>, 16> items_{};
    uint64_t base_{}, session_{}, next_ = 1;
    uint32_t thread_{}, close_error_{};
    void report(Item& item, Packet& packet) {
        const auto status = item.registration.status(GetTickCount64());
        packet.state = static_cast<uint32_t>(status.state);
        packet.cleanup = static_cast<uint32_t>(item.cleanup);
        packet.observed = status.observed; packet.dropped = status.dropped;
        packet.rejected = item.registration.rejected();
    }
public:
    bool begin(uint64_t base, uint64_t session) {
        if (!base || !session || session_) return false;
        for (const auto& item : items_) if (item) return false;
        base_ = base; session_ = session; thread_ = GetCurrentThreadId(); close_error_ = 0;
        return true;
    }
    void maintain() {
        if (!session_ || thread_ != GetCurrentThreadId()) return;
        const auto now = GetTickCount64();
        for (auto& item : items_) if (item) {
            const auto storage = Ops::storage(item->context);
            if (storage != Storage::deferred)
                item->cleanup = item->registration.maintain(storage == Storage::ready, now);
        }
#ifdef E33_BLUEPRINT_DIRECT_SESSION
        bool observed=false;
        for (auto& item : items_) if (item && Ops::is_blueprint(item->context) &&
            item->registration.status(now).state==State::active) observed=true;
        if (!observed) Ops::close_blueprint();
#endif
    }
    bool allows_entry(uint64_t address, uint64_t expected, uint64_t current) const {
        if (!session_ || thread_ != GetCurrentThreadId()) return false;
        for (const auto& item : items_) if (item &&
            reinterpret_cast<uint64_t>(Ops::entry(item->context)) == address &&
            Ops::storage(item->context) == Storage::ready &&
            item->registration.allows_entry(reinterpret_cast<void* volatile*>(address),
                reinterpret_cast<Entry>(expected), reinterpret_cast<Entry>(current))) return true;
        return false;
    }
    void command(Packet& packet) {
        if (!valid_request(packet)) { packet.error = 930; return; }
        if (!session_ || thread_ != GetCurrentThreadId()) { packet.error = 931; return; }
        maintain();
        if (packet.operation == static_cast<uint32_t>(Operation::start)) {
            size_t slot = items_.size();
            for (size_t i = 0; i < items_.size(); ++i) if (!items_[i]) { slot = i; break; }
            if (slot == items_.size()) { packet.error = 932; return; }
            if (!next_) { packet.error = 937; return; }
            auto item = std::unique_ptr<Item>(new(std::nothrow) Item);
            if (!item) { packet.error = 935; return; }
            // Registration uses this native snapshot, never mutable IPC storage.
            auto schema = packet.schema;
            const auto filter = packet.filter;
            if (auto error = Ops::prepare(base_, schema, packet.filtered ? &filter : nullptr, item->context)) {
                packet.error = error; return;
            }
            item->owner = packet.owner; item->id = next_++;
            if (!item->registration.open(Ops::entry(item->context), Ops::expected(base_, schema),
                {session_, item->id}, thread_, packet.duration_ms, packet.limit,
                Ops::collect, &item->context, blueprint_damage_schema(schema))) { packet.error = 936; return; }
            packet.registration = item->id;
            report(*item, packet); items_[slot] = std::move(item); return;
        }
        for (auto& item : items_) if (item && item->owner == packet.owner && item->id == packet.registration) {
            const auto op = static_cast<Operation>(packet.operation);
            if (op == Operation::renew &&
                (Ops::storage(item->context) != Storage::ready ||
                 !item->registration.renew(packet.duration_ms, packet.limit))) {
                packet.error = 939; report(*item, packet); return;
            }
            if (op == Operation::stop || op == Operation::forget) {
                const auto storage = Ops::storage(item->context);
                if (storage == Storage::deferred) { packet.error = 934; report(*item, packet); return; }
                item->cleanup = op == Operation::stop ? item->registration.stop(storage == Storage::ready) :
                                                        item->registration.close(storage == Storage::ready);
            }
            if (op == Operation::drain) {
                Event event{};
                while (packet.count < drain_capacity && item->registration.pop({session_, item->id}, event)) {
                    auto& wire = packet.events[packet.count++];
                    wire.sequence = event.sequence; wire.monotonic_ms = event.monotonic_ms;
                    wire.thread = event.thread; wire.pid = event.object.pid;
                    wire.index = event.object.index; wire.serial = event.object.serial;
                    wire.size = event.value.size; std::memcpy(wire.bytes, event.value.bytes, wire.size);
                }
            }
            report(*item, packet);
            if (op == Operation::forget) item.reset();
            return;
        }
        packet.error = 933;
    }
    // 934 means retry only this cleanup on a later GT message; no new operation.
    uint32_t close(bool terminal) {
        if (!session_) return 0;
        if (thread_ != GetCurrentThreadId()) return 931;
        bool deferred = false;
        for (auto& item : items_) if (item) {
            const auto storage = terminal ? Storage::lost : Ops::storage(item->context);
            if (storage == Storage::deferred) { deferred = true; continue; }
            const auto cleanup = item->registration.close(storage == Storage::ready);
            if (!terminal && cleanup != Cleanup::restored) close_error_ = 938;
            item.reset();
        }
        if (deferred) return 934;
#ifdef E33_BLUEPRINT_DIRECT_SESSION
        Ops::close_blueprint();
#endif
        session_ = base_ = 0; thread_ = 0;
        return close_error_;
    }
};
}
