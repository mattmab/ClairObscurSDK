#pragma once
#include <windows.h>
#include <tlhelp32.h>
#include <string>

struct ModuleSnapshotRead {
    HANDLE handle = INVALID_HANDLE_VALUE;
    DWORD error = ERROR_SUCCESS;
    unsigned attempts = 0;
};

// Windows documents ERROR_BAD_LENGTH when the module list changes while the
// snapshot is taken. Retry that read only, with a bounded seven 1 ms yields.
// Access denied, partial copy, invalid PID, and every other error stay fatal.
// https://learn.microsoft.com/en-us/windows/win32/api/tlhelp32/nf-tlhelp32-createtoolhelp32snapshot
template<class Create, class LastError, class Yield, class RestoreError>
inline ModuleSnapshotRead read_module_snapshot_with(DWORD pid, Create create,
        LastError last_error, Yield yield, RestoreError restore_error) {
    constexpr unsigned limit = 8;
    for (unsigned attempt = 1; attempt <= limit; ++attempt) {
        const HANDLE snapshot = create(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid);
        if (snapshot != INVALID_HANDLE_VALUE) return {snapshot, ERROR_SUCCESS, attempt};
        // Capture before Sleep or any formatting can alter GetLastError.
        const DWORD error = last_error();
        if (error != ERROR_BAD_LENGTH || attempt == limit) {
            restore_error(error);
            return {INVALID_HANDLE_VALUE, error, attempt};
        }
        yield();
    }
    // Every final attempt returns above; this is only a compiler completeness
    // path, never an alternate retry/error policy.
    return {};
}

inline ModuleSnapshotRead read_module_snapshot(DWORD pid) {
    return read_module_snapshot_with(pid,
        [](DWORD flags, DWORD target_pid) { return CreateToolhelp32Snapshot(flags, target_pid); },
        []() { return GetLastError(); }, []() { Sleep(1); },
        [](DWORD error) { SetLastError(error); });
}

inline std::string module_snapshot_failure(const char* label, const ModuleSnapshotRead& result) {
    return std::string(label) + " win32=" + std::to_string(result.error) +
        " attempts=" + std::to_string(result.attempts);
}
