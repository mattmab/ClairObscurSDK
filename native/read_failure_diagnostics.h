#pragma once
#include <cstddef>
#include <cstdint>
#include <iomanip>
#include <sstream>
#include <string>
#include <stdexcept>
#include <windows.h>

// Preserve the Win32 error before querying the failed address: the query can
// itself modify the thread's last-error value. This describes the page at the
// first unread byte, not an atomic snapshot of the original failed read.
inline std::string read_failure_diagnostic(uint64_t address, size_t size,
        size_t received, uint32_t state, uint32_t protection, uint32_t error) {
    std::ostringstream out;
    out << "READ_FAILED address=0x" << std::hex << address << std::dec
        << " size=" << size << " received=" << received
        << " region_state=0x" << std::hex << state
        << " region_protect=0x" << protection << std::dec
        << " win32=" << error;
    return out.str();
}

inline void read_checked_process(HANDLE process, uint64_t address, void* target, size_t size) {
    if (!(address >= 0x10000 && address <= 0x7fffffffffffULL &&
            size <= 2 * 1024 * 1024 && address + size >= address))
        throw std::runtime_error("INVALID_READ_RANGE");
    SIZE_T received = 0;
    const BOOL ok = ReadProcessMemory(process, reinterpret_cast<LPCVOID>(address), target, size, &received);
    const DWORD error = ok ? ERROR_SUCCESS : GetLastError();
    if (ok && received == size) return;
    MEMORY_BASIC_INFORMATION region{};
    const auto offset = received <= size ? received : size;
    // This is a later observation and can differ from the failing read.
    const SIZE_T queried = VirtualQueryEx(process, reinterpret_cast<LPCVOID>(address + offset),
                                           &region, sizeof(region));
    throw std::runtime_error(read_failure_diagnostic(address, size, received,
        queried == sizeof(region) ? region.State : 0,
        queried == sizeof(region) ? region.Protect : 0, error));
}
