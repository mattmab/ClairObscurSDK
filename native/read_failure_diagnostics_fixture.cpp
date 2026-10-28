#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include "read_failure_diagnostics.h"
#include <cassert>

int main() {
    assert(read_failure_diagnostic(0x12340, 128, 32, 0x1000, 0x4, 299) ==
        "READ_FAILED address=0x12340 size=128 received=32 region_state=0x1000 region_protect=0x4 win32=299");
    assert(read_failure_diagnostic(0x10000, 4, 0, 0, 0, 5) ==
        "READ_FAILED address=0x10000 size=4 received=0 region_state=0x0 region_protect=0x0 win32=5");
    SYSTEM_INFO info{};
    GetSystemInfo(&info);
    const size_t page = info.dwPageSize;
    auto* memory = static_cast<unsigned char*>(VirtualAlloc(nullptr, page * 2, MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE));
    assert(memory != nullptr);
    DWORD previous{};
    assert(VirtualProtect(memory + page, page, PAGE_NOACCESS, &previous));
    unsigned char bytes[16]{};
    read_checked_process(GetCurrentProcess(), reinterpret_cast<uint64_t>(memory), bytes, sizeof(bytes));
    bool failed = false;
    try {
        read_checked_process(GetCurrentProcess(), reinterpret_cast<uint64_t>(memory + page), bytes, sizeof(bytes));
    } catch (const std::runtime_error& error) {
        const auto expected = read_failure_diagnostic(reinterpret_cast<uint64_t>(memory + page),
            sizeof(bytes), 0, MEM_COMMIT, PAGE_NOACCESS, ERROR_PARTIAL_COPY);
        assert(expected == error.what());
        failed = true;
    }
    assert(failed);
    assert(VirtualFree(memory, 0, MEM_RELEASE));
}
