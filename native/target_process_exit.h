#pragma once
#include <windows.h>
#include <stdexcept>

struct TargetProcessExited : std::runtime_error {
    DWORD exit_code;
    explicit TargetProcessExited(DWORD code)
        : std::runtime_error("SESSION_TARGET_EXITED"), exit_code(code) {}
};

inline void require_live_target(HANDLE process) {
    if (!process) throw std::runtime_error("SESSION_TARGET_HANDLE_FAILED");
    const DWORD state = WaitForSingleObject(process, 0);
    if (state == WAIT_TIMEOUT) return;
    if (state != WAIT_OBJECT_0) throw std::runtime_error("SESSION_TARGET_WAIT_FAILED");
    DWORD code = 0;
    if (!GetExitCodeProcess(process, &code)) throw std::runtime_error("SESSION_TARGET_EXIT_QUERY_FAILED");
    throw TargetProcessExited(code);
}
