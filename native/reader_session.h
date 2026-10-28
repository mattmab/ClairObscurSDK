// Operation-scoped read-only worker. No UObject observations survive a request.
// Only verified disk-image anchors are reused, under a deny-write/delete handle.
#pragma once
#include "reader_command_policy.h"

using ImageAnchors = std::pair<Anchor, Anchor>;

ImageAnchors image_anchors(const std::filesystem::path& path) {
    const auto image = supported_image(path);
    return {
        resolve_anchor(image, "48 8d 0d ?? ?? ?? ?? 48 8b d7 89 5c 24 20 44 8d 4b ff e8 ?? ?? ?? ?? 48 8b cf"),
        resolve_anchor(image, "4c 8d 05 ?? ?? ?? ?? eb 16 48 8d 0d ?? ?? ?? ?? e8 ?? ?? ?? ?? 4c 8b c0 c6 05 ?? ?? ?? ?? 01 8b d3 0f b7 c3 c1 ea 10 89 44 24 44 89 54 24 40")};
}

struct ReaderSessionGate {
    DWORD pid;
    Handle process;
    Handle file{INVALID_HANDLE_VALUE};
    BY_HANDLE_FILE_INFORMATION identity{};
    uint64_t base = 0;
    ImageAnchors anchors;

    explicit ReaderSessionGate(DWORD expected) : pid(expected),
        process(OpenProcess(SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, FALSE, expected)) {
        require(process.value != nullptr, "READER_PROCESS_OPEN_FAILED");
        require(discover_process(pid) == pid, "READER_PROCESS_CHANGED");
        Handle snapshot(CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid));
        require(snapshot.value != INVALID_HANDLE_VALUE, "READER_MODULE_SNAPSHOT_FAILED");
        MODULEENTRY32W module{}; module.dwSize = sizeof(module);
        require(Module32FirstW(snapshot.value, &module) &&
            _wcsicmp(module.szModule, L"SandFall-Win64-Shipping.exe") == 0 &&
            module.modBaseSize == 166776832, "READER_MODULE_MISMATCH");
        file.value = CreateFileW(module.szExePath, GENERIC_READ, FILE_SHARE_READ,
            nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
        require(file.value != INVALID_HANDLE_VALUE, "READER_IMAGE_LOCK_FAILED");
        require(GetFileInformationByHandle(file.value, &identity), "READER_FILE_ID_FAILED");
        base = reinterpret_cast<uint64_t>(module.modBaseAddr);
        anchors = image_anchors(module.szExePath);
        validate(pid, module);
    }

    void validate(DWORD observed_pid, const MODULEENTRY32W& module) const {
        require(observed_pid == pid && WaitForSingleObject(process.value, 0) == WAIT_TIMEOUT,
            "READER_ORIGINAL_PROCESS_EXITED_OR_CHANGED");
        require(reinterpret_cast<uint64_t>(module.modBaseAddr) == base &&
            module.modBaseSize == 166776832, "READER_MODULE_CHANGED");
        // Check file identity, not just a path string (including reparse changes).
        Handle current(CreateFileW(module.szExePath, GENERIC_READ, FILE_SHARE_READ,
            nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr));
        BY_HANDLE_FILE_INFORMATION observed{};
        require(current.value != INVALID_HANDLE_VALUE &&
            GetFileInformationByHandle(current.value, &observed), "READER_IMAGE_RECHECK_FAILED");
        require(observed.dwVolumeSerialNumber == identity.dwVolumeSerialNumber &&
            observed.nFileIndexHigh == identity.nFileIndexHigh &&
            observed.nFileIndexLow == identity.nFileIndexLow &&
            observed.nFileSizeHigh == identity.nFileSizeHigh &&
            observed.nFileSizeLow == identity.nFileSizeLow, "READER_IMAGE_ID_CHANGED");
    }
};

// Single-threaded stdin loop only. Never used by an ordinary probe invocation.
static const ReaderSessionGate* active_reader_gate = nullptr;

ImageAnchors observed_image_anchors(DWORD pid, const MODULEENTRY32W& module) {
    if (!active_reader_gate) return image_anchors(module.szExePath);
    active_reader_gate->validate(pid, module);
    return active_reader_gate->anchors;
}

int run_reader_session(const std::string& expected_pid, int (*query)(int, char**)) {
    try {
        require(!expected_pid.empty() && expected_pid.size() <= 10 &&
            expected_pid.find_first_not_of("0123456789") == std::string::npos,
            "READER_PID_INVALID");
        const auto value = std::stoull(expected_pid);
        require(value > 0 && value <= 0xffffffffULL, "READER_PID_INVALID");
        ReaderSessionGate gate(static_cast<DWORD>(value));
        active_reader_gate = &gate;
        std::cout << "{\"event\":\"reader_ready\",\"version\":3,\"pid\":" << gate.pid << "}\n" << std::flush;
        uint64_t sequence = 0;
        while (true) {
            std::string line;
            char c;
            while (std::cin.get(c) && c != '\n') {
                require(line.size() < 131072 && c != '\r' && c != '\0', "READER_REQUEST_INVALID");
                line += c;
            }
            if (!std::cin && line.empty()) break;
            require(bool(std::cin), "READER_REQUEST_TRUNCATED");
            std::vector<std::string> arguments;
            std::istringstream input(line); std::string token;
            while (std::getline(input, token, '\t')) arguments.push_back(token);
            require(reader_arguments(arguments, gate.pid), "READER_OPERATION_NOT_ALLOWED");
            arguments.insert(arguments.begin(), "research-reader");
            std::vector<char*> argv;
            for (auto& argument : arguments) argv.push_back(argument.data());
            // Query errors are JSON and belong to the same framed reply.
            auto previous = std::cerr.rdbuf(std::cout.rdbuf());
            const int result = query(static_cast<int>(argv.size()), argv.data());
            std::cerr.rdbuf(previous);
            std::cout << "{\"event\":\"reader_result\",\"sequence\":" << ++sequence
                << ",\"code\":" << result << "}\n" << std::flush;
            if (result) { active_reader_gate = nullptr; return result; }
        }
        active_reader_gate = nullptr;
        return 0;
    } catch (const std::exception& error) {
        active_reader_gate = nullptr;
        std::cout << "{\"event\":\"reader_error\",\"message\":" << quote(error.what()) << "}\n" << std::flush;
        return 1;
    }
}
