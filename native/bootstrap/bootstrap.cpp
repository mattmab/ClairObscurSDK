// Independently authored SDK bootstrap. No third-party mod code or binary.
// Exact x64 tail forwarding preserves even undocumented VERSION export ABIs.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <filesystem>
#include <string>
#include "export_names.h"

static INIT_ONCE version_once = INIT_ONCE_STATIC_INIT;
static HMODULE system_version = nullptr;
static HMODULE bootstrap_module = nullptr;

static BOOL CALLBACK load_system_version(PINIT_ONCE, PVOID, PVOID*) {
    wchar_t directory[32768]{};
    const UINT count = GetSystemDirectoryW(directory, 32768);
    if (!count || count >= 32768) return FALSE;
    std::wstring path(directory);
    path += L"\\version.dll";
    system_version = LoadLibraryExW(path.c_str(), nullptr, LOAD_LIBRARY_SEARCH_SYSTEM32);
    return system_version != nullptr;
}

extern "C" FARPROC ResolveVersionExport(unsigned index) {
    const DWORD saved_error = GetLastError();
    if (index >= sizeof(export_names) / sizeof(export_names[0]) ||
        !InitOnceExecuteOnce(&version_once, load_system_version, nullptr, nullptr)) {
        RaiseFailFastException(nullptr, nullptr, 0);
        return nullptr;
    }
    FARPROC result = GetProcAddress(system_version, export_names[index]);
    if (!result) RaiseFailFastException(nullptr, nullptr, 0);
    SetLastError(saved_error);
    return result;
}

static DWORD WINAPI start_controller(LPVOID) {
    // This thread cannot enter until DLL initialization releases the loader lock.
    // No waits, process creation, or Python initialization occur in DllMain.
    try {
        wchar_t executable[32768]{}, library[32768]{};
        const DWORD e = GetModuleFileNameW(nullptr, executable, 32768);
        const DWORD d = GetModuleFileNameW(bootstrap_module, library, 32768);
        if (!e || e >= 32768 || !d || d >= 32768) return 1;
        const std::filesystem::path game(executable), self(library);
        if (_wcsicmp(game.filename().c_str(), L"SandFall-Win64-Shipping.exe") != 0 ||
            game.parent_path() != self.parent_path()) return 0;
        const auto root = game.parent_path().parent_path().parent_path().parent_path();
        const auto sdk = root / L"SDK";
        if (std::filesystem::exists(sdk / L"autostart.disabled")) return 0;
        const auto python = sdk / L"runtime" / L"pythonw.exe";
        const auto script = sdk / L"scripts" / L"run_release_sdk.py";
        if (!std::filesystem::is_regular_file(python) || !std::filesystem::is_regular_file(script)) return 2;
        std::wstring command = L"\"" + python.wstring() + L"\" -I -S -B \"" + script.wstring() +
            L"\" --game-pid " + std::to_wstring(GetCurrentProcessId());
        if (std::filesystem::exists(sdk / L"developer-commands.enabled")) command += L" --commands";
        STARTUPINFOW startup{}; startup.cb = sizeof(startup);
        startup.dwFlags = STARTF_USESHOWWINDOW; startup.wShowWindow = SW_HIDE;
        PROCESS_INFORMATION process{};
        if (!CreateProcessW(python.c_str(), command.data(), nullptr, nullptr, FALSE,
                            CREATE_NO_WINDOW, nullptr, sdk.c_str(), &startup, &process)) return GetLastError();
        CloseHandle(process.hThread); CloseHandle(process.hProcess);
        return 0;
    } catch (...) { return 3; }
}

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        bootstrap_module = instance;
        DisableThreadLibraryCalls(instance);
        HANDLE thread = CreateThread(nullptr, 0, start_controller, nullptr, 0, nullptr);
        if (thread) CloseHandle(thread);
    }
    return TRUE;
}
