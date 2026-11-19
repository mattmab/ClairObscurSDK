// Operation-scoped read-only worker. No UObject observations survive a request.
// Only verified image metadata and the pinned process/module binding survive;
// the executable remains held under a deny-write/delete file handle.
#pragma once
#include "reader_command_policy.h"
#include "module_snapshot_read.h"

using ImageAnchors = std::pair<Anchor, Anchor>;
struct ReaderImageHeaders {
    IMAGE_DOS_HEADER dos{};
    IMAGE_NT_HEADERS64 nt{};
};

ImageAnchors image_anchors(const std::filesystem::path& path, ReaderImageHeaders* headers = nullptr) {
    const auto image = supported_image(path);
    if(headers) {
        std::memcpy(&headers->dos,image.data(),sizeof(headers->dos));
        require(headers->dos.e_magic==IMAGE_DOS_SIGNATURE && headers->dos.e_lfanew>0 &&
            size_t(headers->dos.e_lfanew)<=image.size()-sizeof(headers->nt),"READER_DISK_HEADERS_INVALID");
        std::memcpy(&headers->nt,image.data()+headers->dos.e_lfanew,sizeof(headers->nt));
        require(headers->nt.Signature==IMAGE_NT_SIGNATURE && headers->nt.FileHeader.Machine==IMAGE_FILE_MACHINE_AMD64 &&
            headers->nt.OptionalHeader.Magic==IMAGE_NT_OPTIONAL_HDR64_MAGIC &&
            headers->nt.OptionalHeader.SizeOfImage==166776832,"READER_DISK_IMAGE_INVALID");
    }
    return {
        resolve_anchor(image, "48 8d 0d ?? ?? ?? ?? 48 8b d7 89 5c 24 20 44 8d 4b ff e8 ?? ?? ?? ?? 48 8b cf"),
        resolve_anchor(image, "4c 8d 05 ?? ?? ?? ?? eb 16 48 8d 0d ?? ?? ?? ?? e8 ?? ?? ?? ?? 4c 8b c0 c6 05 ?? ?? ?? ?? 01 8b d3 0f b7 c3 c1 ea 10 89 44 24 44 89 54 24 40")};
}

inline bool reader_image_identity_equal(const BY_HANDLE_FILE_INFORMATION& a,const BY_HANDLE_FILE_INFORMATION& b) {
    return a.dwVolumeSerialNumber==b.dwVolumeSerialNumber && a.nFileIndexHigh==b.nFileIndexHigh &&
        a.nFileIndexLow==b.nFileIndexLow && a.nFileSizeHigh==b.nFileSizeHigh && a.nFileSizeLow==b.nFileSizeLow;
}
inline bool reader_module_mapping_valid(const MEMORY_BASIC_INFORMATION& memory,uint64_t base) {
    return memory.State==MEM_COMMIT && memory.Type==MEM_IMAGE &&
        reinterpret_cast<uint64_t>(memory.AllocationBase)==base &&
        reinterpret_cast<uint64_t>(memory.BaseAddress)==base;
}
inline bool reader_image_headers_equal(const ReaderImageHeaders& live,const ReaderImageHeaders& disk,uint64_t base) {
    // The observed loaded image rewrites OptionalHeader.ImageBase for ASLR.
    // Permit exactly the verified allocation base; every other header byte
    // must still match the fingerprint-verified disk image.
    auto relocated=disk;relocated.nt.OptionalHeader.ImageBase=base;
    return !std::memcmp(&live.dos,&relocated.dos,sizeof(live.dos)) && !std::memcmp(&live.nt,&relocated.nt,sizeof(live.nt));
}
template<class Checks> void validate_reader_session_request(Checks& checks) {
    // No process/module enumeration and no UObject observations are retained.
    // Every request proves the pinned process, file and loaded image afresh.
    require(checks.process_alive(),"READER_ORIGINAL_PROCESS_EXITED_OR_CHANGED");
    require(checks.image_identity(),"READER_IMAGE_ID_CHANGED");
    require(checks.module_mapping(),"READER_MODULE_MAPPING_CHANGED");
    require(checks.image_headers(),"READER_MODULE_HEADERS_CHANGED");
}

struct ReaderSessionGate {
    DWORD pid;
    Handle process;
    Handle file{INVALID_HANDLE_VALUE};
    BY_HANDLE_FILE_INFORMATION identity{};
    uint64_t base = 0;
    ImageAnchors anchors;
    MODULEENTRY32W module{};
    ReaderImageHeaders headers{};

    explicit ReaderSessionGate(DWORD expected) : pid(expected),
        process(OpenProcess(SYNCHRONIZE | PROCESS_VM_READ | PROCESS_QUERY_LIMITED_INFORMATION, FALSE, expected)) {
        require(process.value != nullptr, "READER_PROCESS_OPEN_FAILED");
        require(discover_process(pid) == pid, "READER_PROCESS_CHANGED");
        const auto module_snapshot = read_module_snapshot(pid);
        Handle snapshot(module_snapshot.handle);
        require(snapshot.value != INVALID_HANDLE_VALUE, module_snapshot_failure("READER_MODULE_SNAPSHOT_FAILED", module_snapshot));
        module.dwSize = sizeof(module);
        require(Module32FirstW(snapshot.value, &module) &&
            _wcsicmp(module.szModule, L"SandFall-Win64-Shipping.exe") == 0 &&
            module.modBaseSize == 166776832, "READER_MODULE_MISMATCH");
        file.value = CreateFileW(module.szExePath, GENERIC_READ, FILE_SHARE_READ,
            nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
        require(file.value != INVALID_HANDLE_VALUE, "READER_IMAGE_LOCK_FAILED");
        require(GetFileInformationByHandle(file.value, &identity), "READER_FILE_ID_FAILED");
        base = reinterpret_cast<uint64_t>(module.modBaseAddr);
        anchors = image_anchors(module.szExePath,&headers);
        validate(pid, module);
    }

    void validate(DWORD observed_pid, const MODULEENTRY32W& observed_module) const {
        require(observed_pid == pid,"READER_PROCESS_CHANGED");
        require(reinterpret_cast<uint64_t>(observed_module.modBaseAddr) == base &&
            observed_module.modBaseSize == 166776832, "READER_MODULE_CHANGED");
        struct Checks {
            const ReaderSessionGate& gate;
            bool process_alive() const {
                return GetProcessId(gate.process.value)==gate.pid &&
                    WaitForSingleObject(gate.process.value,0)==WAIT_TIMEOUT;
            }
            bool image_identity() const {
                // Resolve the process's image path again, then compare actual
                // file identity. Ancestor reparse changes cannot pass by name.
                std::wstring path(32768,L'\0');DWORD length=static_cast<DWORD>(path.size());
                require(QueryFullProcessImageNameW(gate.process.value,0,path.data(),&length) && length>0 &&
                    length<path.size(),"READER_IMAGE_PATH_RECHECK_FAILED");
                path.resize(length);
                Handle current(CreateFileW(path.c_str(),GENERIC_READ,FILE_SHARE_READ,
                    nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr));
                BY_HANDLE_FILE_INFORMATION observed{};
                require(current.value!=INVALID_HANDLE_VALUE && GetFileInformationByHandle(current.value,&observed),
                    "READER_IMAGE_RECHECK_FAILED");
                return reader_image_identity_equal(observed,gate.identity);
            }
            bool module_mapping() const {
                MEMORY_BASIC_INFORMATION memory{};
                return VirtualQueryEx(gate.process.value,reinterpret_cast<const void*>(gate.base),&memory,sizeof(memory))==sizeof(memory) &&
                    reader_module_mapping_valid(memory,gate.base);
            }
            bool image_headers() const {
                // Expected offset and bytes come from the fingerprint-verified
                // locked disk image, never from a mutable target pointer.
                Reader reader{gate.process.value};ReaderImageHeaders live{};
                reader.read(gate.base,&live.dos,sizeof(live.dos));
                reader.read(gate.base+uint64_t(gate.headers.dos.e_lfanew),&live.nt,sizeof(live.nt));
                return reader_image_headers_equal(live,gate.headers,gate.base);
            }
        } checks{*this};
        validate_reader_session_request(checks);
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
