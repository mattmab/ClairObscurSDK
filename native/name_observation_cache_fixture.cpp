#include "name_observation_cache.h"
#include <cassert>
#include <stdexcept>
#include <string>

int main() {
    NameObservationCache cache(2);
    unsigned reads = 0;
    auto source = [&](uint64_t pool, uint32_t id, uint32_t number) {
        ++reads;
        return std::to_string(pool) + ":" + std::to_string(id) + ":" + std::to_string(number);
    };
    assert(cache.read(10, 20, 0, source) == "10:20:0");
    assert(cache.read(10, 20, 0, source) == "10:20:0" && reads == 1);
    assert(cache.read(11, 20, 0, source) == "11:20:0" && reads == 2);
    assert(cache.size() == 2);
    // Overflow is read each time rather than growing unbounded.
    assert(cache.read(10, 20, 1, source) == "10:20:1");
    assert(cache.read(10, 20, 1, source) == "10:20:1" && reads == 4);
    assert(cache.validate(source) && reads == 6);
    assert(!cache.validate([](uint64_t, uint32_t, uint32_t) { return std::string("changed"); }));
    NameObservationCache failed;
    try {
        failed.read(10, 20, 0, [](uint64_t, uint32_t, uint32_t) -> std::string {
            throw std::runtime_error("failed read");
        });
        assert(false);
    } catch (const std::runtime_error&) {}
    assert(failed.size() == 0);
    assert(failed.read(10, 20, 0, source) == "10:20:0");
}
