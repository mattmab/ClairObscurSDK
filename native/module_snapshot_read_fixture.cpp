#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include "module_snapshot_read.h"
#include <cassert>
#include <cstdint>
#include <initializer_list>
#include <vector>

struct SnapshotScenario {
    std::vector<DWORD> results;
    unsigned creates = 0, yields = 0, reads = 0, restores = 0;
    HANDLE success = reinterpret_cast<HANDLE>(static_cast<uintptr_t>(0x1234));
    ModuleSnapshotRead run() {
        return read_module_snapshot_with(42,
            [this](DWORD flags, DWORD pid) {
                assert(flags == (TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32));
                assert(pid == 42 && creates < results.size());
                const auto code = results[creates++];
                SetLastError(code);
                return code == ERROR_SUCCESS ? success : INVALID_HANDLE_VALUE;
            },
            [this]() { ++reads; return GetLastError(); },
            [this]() { ++yields; SetLastError(ERROR_TIMEOUT); },
            [this](DWORD error) { ++restores; SetLastError(error); });
    }
};

int main() {
    {
        SnapshotScenario test{{ERROR_SUCCESS}};
        const auto result = test.run();
        assert(result.handle == test.success && result.error == ERROR_SUCCESS && result.attempts == 1);
        assert(test.creates == 1 && test.yields == 0 && test.reads == 0 && test.restores == 0);
    }
    {
        SnapshotScenario test{{ERROR_BAD_LENGTH, ERROR_BAD_LENGTH, ERROR_SUCCESS}};
        const auto result = test.run();
        assert(result.handle == test.success && result.error == ERROR_SUCCESS && result.attempts == 3);
        assert(test.creates == 3 && test.yields == 2 && test.reads == 2 && test.restores == 0);
    }
    for (DWORD permanent : {ERROR_ACCESS_DENIED, ERROR_PARTIAL_COPY, ERROR_INVALID_PARAMETER, ERROR_NOT_FOUND}) {
        SnapshotScenario test{{permanent, ERROR_SUCCESS}};
        const auto result = test.run();
        const auto preserved = GetLastError();
        assert(result.handle == INVALID_HANDLE_VALUE && result.error == permanent && result.attempts == 1);
        assert(preserved == permanent && test.creates == 1 && test.yields == 0 && test.restores == 1);
    }
    {
        SnapshotScenario test{{ERROR_BAD_LENGTH, ERROR_ACCESS_DENIED, ERROR_SUCCESS}};
        const auto result = test.run();
        const auto preserved = GetLastError();
        assert(result.handle == INVALID_HANDLE_VALUE && result.error == ERROR_ACCESS_DENIED && result.attempts == 2);
        assert(preserved == ERROR_ACCESS_DENIED && test.creates == 2 && test.yields == 1 && test.restores == 1);
        assert(module_snapshot_failure("MODULE_SNAPSHOT_FAILED", result) == "MODULE_SNAPSHOT_FAILED win32=5 attempts=2");
    }
    {
        SnapshotScenario test{{ERROR_BAD_LENGTH, ERROR_BAD_LENGTH, ERROR_BAD_LENGTH, ERROR_BAD_LENGTH,
            ERROR_BAD_LENGTH, ERROR_BAD_LENGTH, ERROR_BAD_LENGTH, ERROR_BAD_LENGTH, ERROR_SUCCESS}};
        const auto result = test.run();
        const auto preserved = GetLastError();
        assert(result.handle == INVALID_HANDLE_VALUE && result.error == ERROR_BAD_LENGTH && result.attempts == 8);
        assert(preserved == ERROR_BAD_LENGTH && test.creates == 8 && test.yields == 7 && test.reads == 8 && test.restores == 1);
    }
    // The production wrapper also preserves ownership of a successful handle;
    // this local process read has no relationship to the running game/session.
    const auto local = read_module_snapshot(GetCurrentProcessId());
    assert(local.handle != INVALID_HANDLE_VALUE && local.error == ERROR_SUCCESS);
    MODULEENTRY32W entry{}; entry.dwSize = sizeof(entry);
    assert(Module32FirstW(local.handle, &entry));
    assert(CloseHandle(local.handle));
}
