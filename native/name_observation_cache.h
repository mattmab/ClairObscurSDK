#pragma once

#include <cstddef>
#include <cstdint>
#include <functional>
#include <string>
#include <unordered_map>

// Per-query name copies only. The caller must perform validate() before
// accepting the observation and discard the whole query if a name changed.
// No cached name survives a query or implies that an engine object is alive.
class NameObservationCache {
    struct Key {
        uint64_t pool;
        uint32_t id, number;
        bool operator==(const Key& other) const noexcept {
            return pool == other.pool && id == other.id && number == other.number;
        }
    };
    struct Hash {
        size_t operator()(const Key& key) const noexcept {
            const auto a = std::hash<uint64_t>{}(key.pool);
            const auto b = std::hash<uint64_t>{}((uint64_t(key.number) << 32) | key.id);
            return a ^ (b + size_t(0x9e3779b9U) + (a << 6) + (a >> 2));
        }
    };
    std::unordered_map<Key, std::string, Hash> entries_;
    size_t limit_;
public:
    static constexpr size_t maximum_entries = 16384;
    explicit NameObservationCache(size_t limit = maximum_entries) : limit_(limit) {
        if (limit_ > maximum_entries) limit_ = maximum_entries;
    }
    template<class Read>
    std::string read(uint64_t pool, uint32_t id, uint32_t number, Read&& source) {
        Key key{pool, id, number};
        const auto found = entries_.find(key);
        if (found != entries_.end()) return found->second;
        auto value = source(pool, id, number);
        if (entries_.size() < limit_) entries_.emplace(key, value);
        return value;
    }
    template<class Read>
    bool validate(Read&& source) const {
        for (const auto& entry : entries_) {
            if (source(entry.first.pool, entry.first.id, entry.first.number) != entry.second)
                return false;
        }
        return true;
    }
    size_t size() const noexcept { return entries_.size(); }
};
