#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include "target_process_exit.h"
#include <cstdlib>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
    if (argc == 2) return std::atoi(argv[1]);
    try {
        require_live_target(GetCurrentProcess());
        bool rejected = false;
        try { require_live_target(nullptr); } catch (const TargetProcessExited&) { return 2; }
        catch (const std::runtime_error&) { rejected = true; }
        if (!rejected) return 3;
        for (DWORD expected : {0u, 7u, 259u}) {
            wchar_t path[32768];
            if (!GetModuleFileNameW(nullptr, path, 32768)) return 4;
            std::wstring command = L"\"" + std::wstring(path) + L"\" " + std::to_wstring(expected);
            STARTUPINFOW startup{}; startup.cb = sizeof(startup);
            PROCESS_INFORMATION child{};
            if (!CreateProcessW(path, command.data(), nullptr, nullptr, FALSE, CREATE_NO_WINDOW,
                                nullptr, nullptr, &startup, &child)) return 5;
            CloseHandle(child.hThread);
            if (WaitForSingleObject(child.hProcess, 10000) != WAIT_OBJECT_0) { CloseHandle(child.hProcess); return 6; }
            bool matched = false;
            try { require_live_target(child.hProcess); }
            catch (const TargetProcessExited& exit) { matched = exit.exit_code == expected; }
            CloseHandle(child.hProcess);
            if (!matched) return 7;
        }
        std::cout << "Live handle, invalid handle and three confirmed exit codes passed.\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n'; return 8;
    }
}
