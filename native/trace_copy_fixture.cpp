#include "trace_copy.h"
#include <cassert>
#include <cstdio>
#include <limits>

int main() {
    using namespace e33_trace;
    uint8_t locals[] = {11, 12, 99, 99, 99, 99, 99, 99};
    uint8_t result[] = {42};
    uint8_t out[] = {21, 22};
    View sources[] = {{locals, sizeof(locals)}, {result, sizeof(result)}, {out, sizeof(out)}};
    Field fields[] = {{0, 0, 0, 2}, {2, 0, 2, 2}, {1, 0, 4, 1}};
    Copy copied{};
    assert(copy_fields(sources, 3, fields, 3, 8, copied) == CopyError::none);
    assert(copied.size == 8 && copied.bytes[0] == 11 && copied.bytes[1] == 12);
    assert(copied.bytes[2] == 21 && copied.bytes[3] == 22 && copied.bytes[4] == 42);
    assert(copied.bytes[5] == 0 && copied.bytes[6] == 0 && copied.bytes[7] == 0);
    locals[0] = result[0] = out[0] = 0;
    assert(copied.bytes[0] == 11 && copied.bytes[2] == 21 && copied.bytes[4] == 42);
    auto reject = [&](Field field, CopyError expected) {
        Field bad[] = {fields[0], field};
        copied.size = 7; copied.bytes[0] = 255;
        assert(copy_fields(sources, 3, bad, 2, 8, copied) == expected);
        assert(copied.size == 0);
        for (auto byte : copied.bytes) assert(byte == 0);
    };
    reject({1, 0, 1, 1}, CopyError::overlap);
    reject({3, 0, 2, 1}, CopyError::source);
    reject({1, 0, 2, 2}, CopyError::range);
    reject({0, std::numeric_limits<uint32_t>::max(), 2, 2}, CopyError::range);
    reject({0, 0, std::numeric_limits<uint32_t>::max(), 2}, CopyError::range);
    reject({0, 0, 8, 1}, CopyError::range);
    reject({0, 0, 2, 0}, CopyError::range);
    sources[1].data = nullptr;
    reject({1, 0, 2, 1}, CopyError::source);
    assert(copy_fields(nullptr, 1, fields, 3, 8, copied) == CopyError::limits);
    assert(copy_fields(sources, max_sources + 1, fields, 3, 8, copied) == CopyError::limits);
    assert(copy_fields(sources, 3, fields, max_fields + 1, 8, copied) == CopyError::limits);
    assert(copy_fields(sources, 3, fields, 3, max_bytes + 1, copied) == CopyError::limits);
    assert(copy_fields(nullptr, 0, nullptr, 0, 0, copied) == CopyError::none);
    assert(copied.size == 0);
    std::puts("Trace copying: independent locals/out/result, owned bytes, zero padding and fail-closed bounds passed.");
}
