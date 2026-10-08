// Read-only research probe. Build-scoped layouts corroborated by live identity checks.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <tlhelp32.h>
#include <bcrypt.h>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

struct Handle {
    HANDLE value;
    explicit Handle(HANDLE v) : value(v) {}
    ~Handle() { if (value && value != INVALID_HANDLE_VALUE) CloseHandle(value); }
    Handle(const Handle&) = delete;
};

std::string hex(uint64_t value) {
    std::ostringstream out; out << "0x" << std::hex << value; return out.str();
}
std::string quote(const std::string& value) {
    std::ostringstream out; out << '"';
    for (unsigned char c : value) {
        if (c == '"' || c == '\\') out << '\\' << char(c);
        else if (c < 32) out << "\\u" << std::hex << std::setw(4) << std::setfill('0') << unsigned(c);
        else out << char(c);
    }
    out << '"'; return out.str();
}
void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}
std::string sha256(const std::vector<uint8_t>& bytes) {
    BCRYPT_ALG_HANDLE alg = nullptr;
    BCRYPT_HASH_HANDLE hash = nullptr;
    require(BCryptOpenAlgorithmProvider(&alg, BCRYPT_SHA256_ALGORITHM, nullptr, 0) >= 0,
            "HASH_PROVIDER_FAILED");
    DWORD length = 0, returned = 0;
    auto status = BCryptGetProperty(alg, BCRYPT_OBJECT_LENGTH,
        reinterpret_cast<PUCHAR>(&length), sizeof(length), &returned, 0);
    std::vector<uint8_t> object(length);
    if (status >= 0) status = BCryptCreateHash(alg, &hash, object.data(), length, nullptr, 0, 0);
    uint8_t digest[32]{};
    if (status >= 0) status = BCryptHashData(hash, const_cast<PUCHAR>(bytes.data()),
                                           static_cast<ULONG>(bytes.size()), 0);
    if (status >= 0) status = BCryptFinishHash(hash, digest, sizeof(digest), 0);
    if (hash) BCryptDestroyHash(hash);
    BCryptCloseAlgorithmProvider(alg, 0);
    require(status >= 0, "HASH_FAILED");
    std::ostringstream out;
    for (auto byte : digest) out << std::hex << std::setw(2) << std::setfill('0') << unsigned(byte);
    return out.str();
}

struct Reader {
    HANDLE process;
    void read(uint64_t address, void* target, size_t size) const {
        require(address >= 0x10000 && address <= 0x7fffffffffffULL &&
                size <= 2 * 1024 * 1024 && address + size >= address, "INVALID_READ_RANGE");
        SIZE_T received = 0;
        if (!ReadProcessMemory(process, reinterpret_cast<LPCVOID>(address), target, size, &received)
            || received != size)
            throw std::runtime_error("READ_FAILED address=" + hex(address) +
                                     " win32=" + std::to_string(GetLastError()));
    }
    template<class T> T get(uint64_t address) const {
        T value{}; read(address, &value, sizeof(value)); return value;
    }
};

DWORD discover_process() {
    Handle snapshot(CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0));
    require(snapshot.value != INVALID_HANDLE_VALUE, "PROCESS_SNAPSHOT_FAILED");
    PROCESSENTRY32W entry{}; entry.dwSize = sizeof(entry);
    DWORD pid = 0;
    for (BOOL more = Process32FirstW(snapshot.value, &entry); more;
         more = Process32NextW(snapshot.value, &entry)) {
        if (_wcsicmp(entry.szExeFile, L"SandFall-Win64-Shipping.exe") == 0) {
            require(pid == 0, "MULTIPLE_GAME_PROCESSES"); pid = entry.th32ProcessID;
        }
    }
    require(pid != 0, "GAME_NOT_RUNNING"); return pid;
}

struct Anchor { uint32_t instruction_rva; uint32_t global_rva; std::vector<uint8_t> original; };
Anchor resolve_anchor(const std::vector<uint8_t>& image, const std::string& signature) {
    std::vector<int> pattern; std::istringstream stream(signature); std::string token;
    while (stream >> token) pattern.push_back(token == "??" ? -1 : std::stoi(token, nullptr, 16));
    auto dos = reinterpret_cast<const IMAGE_DOS_HEADER*>(image.data());
    auto nt = reinterpret_cast<const IMAGE_NT_HEADERS64*>(image.data() + dos->e_lfanew);
    const auto* sections = IMAGE_FIRST_SECTION(nt);
    std::vector<Anchor> found;
    for (unsigned s = 0; s < nt->FileHeader.NumberOfSections; ++s) {
        const auto& section = sections[s];
        if (!(section.Characteristics & IMAGE_SCN_MEM_EXECUTE)) continue;
        for (size_t i = 0; i + pattern.size() <= section.SizeOfRawData; ++i) {
            const uint8_t* ptr = image.data() + section.PointerToRawData + i;
            if (ptr[0] != pattern[0]) continue;
            bool equal = true;
            for (size_t j = 1; j < pattern.size(); ++j)
                if (pattern[j] >= 0 && ptr[j] != pattern[j]) { equal = false; break; }
            if (!equal) continue;
            int32_t displacement; std::memcpy(&displacement, ptr + 3, 4);
            uint32_t rva = section.VirtualAddress + static_cast<uint32_t>(i);
            int64_t global = int64_t(rva) + 7 + displacement;
            require(global > 0 && global < nt->OptionalHeader.SizeOfImage - 0x10010,
                    "ANCHOR_TARGET_OUTSIDE_IMAGE");
            found.push_back({rva, static_cast<uint32_t>(global),
                             std::vector<uint8_t>(ptr, ptr + pattern.size())});
        }
    }
    require(found.size() == 1, "SIGNATURE_MATCH_COUNT=" + std::to_string(found.size()));
    return found.front();
}

struct ObjectHeader {
    uint64_t vtable; uint32_t flags; int32_t index; uint64_t cls;
    uint32_t name_id; uint32_t name_number; uint64_t outer;
};
struct ObjectItem { uint64_t object; uint32_t flags; int32_t cluster; int32_t serial; uint32_t pad; };
struct ArrayHeader { uint64_t chunks, preallocated; int32_t max_elements, num_elements, max_chunks, num_chunks; };
static_assert(sizeof(ObjectHeader) == 40 && sizeof(ObjectItem) == 24 && sizeof(ArrayHeader) == 32);

std::string read_name(const Reader& reader, uint64_t pool, uint32_t id, uint32_t number = 0) {
    uint32_t block = id >> 16, offset = (id & 0xffff) * 2;
    require(block < 8192, "NAME_BLOCK_OUT_OF_RANGE");
    uint64_t pointer = reader.get<uint64_t>(pool + 0x10 + uint64_t(block) * 8);
    uint16_t header = reader.get<uint16_t>(pointer + offset);
    uint32_t length = header >> 6, width = (header & 1) ? 2 : 1;
    require(length > 0 && length <= 1023 && offset + 2 + length * width <= 0x20000,
            "NAME_ENTRY_INVALID");
    std::string value;
    if (width == 1) {
        value.resize(length); reader.read(pointer + offset + 2, value.data(), length);
        for (unsigned char c : value) require(c >= 32 && c < 127, "NON_ASCII_NARROW_NAME");
    } else {
        std::wstring wide(length, 0); reader.read(pointer + offset + 2, wide.data(), length * 2);
        int size = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, wide.data(),
                                      static_cast<int>(length), nullptr, 0, nullptr, nullptr);
        require(size > 0, "INVALID_WIDE_NAME"); value.resize(size);
        WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, wide.data(), static_cast<int>(length),
                            value.data(), size, nullptr, nullptr);
    }
    if (number) value += "_" + std::to_string(number - 1);
    return value;
}

int main(int argc, char** argv) {
    try {
        uint32_t limit = 32;
        if (argc == 3 && std::string(argv[1]) == "--limit") limit = std::stoul(argv[2]);
        else require(argc == 1, "USAGE: research_probe.exe [--limit N]; 0 means all occupied slots");
        DWORD pid = discover_process();
        Handle process(OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid));
        require(process.value != nullptr, "OPEN_PROCESS_FAILED win32=" + std::to_string(GetLastError()));
        Handle snapshot(CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid));
        require(snapshot.value != INVALID_HANDLE_VALUE, "MODULE_SNAPSHOT_FAILED");
        MODULEENTRY32W module{}; module.dwSize = sizeof(module);
        require(Module32FirstW(snapshot.value, &module) != FALSE, "MODULE_NOT_FOUND");
        require(_wcsicmp(module.szModule, L"SandFall-Win64-Shipping.exe") == 0, "UNEXPECTED_MAIN_MODULE");
        std::ifstream file(std::filesystem::path(module.szExePath), std::ios::binary | std::ios::ate);
        require(bool(file), "MODULE_FILE_OPEN_FAILED");
        require(file.tellg() == 162421568, "UNSUPPORTED_BUILD_SIZE");
        std::vector<uint8_t> image(162421568); file.seekg(0);
        file.read(reinterpret_cast<char*>(image.data()), image.size());
        require(bool(file), "MODULE_FILE_READ_FAILED");
        const auto fingerprint = sha256(image);
        require(fingerprint == "218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618",
                "UNSUPPORTED_BUILD_SHA256=" + fingerprint);
        auto registry = resolve_anchor(image, "48 8d 0d ?? ?? ?? ?? 48 8b d7 89 5c 24 20 44 8d 4b ff e8 ?? ?? ?? ?? 48 8b cf");
        auto names = resolve_anchor(image, "4c 8d 05 ?? ?? ?? ?? eb 16 48 8d 0d ?? ?? ?? ?? e8 ?? ?? ?? ?? 4c 8b c0 c6 05 ?? ?? ?? ?? 01 8b d3 0f b7 c3 c1 ea 10 89 44 24 44 89 54 24 40");
        require(registry.global_rva == 0x9361b60 && names.global_rva == 0x92aadc0,
                "DISCOVERY_DISAGREES_WITH_STATIC_EVIDENCE");
        const uint64_t base = reinterpret_cast<uint64_t>(module.modBaseAddr);
        require(module.modBaseSize == 166776832, "UNSUPPORTED_RUNTIME_IMAGE_SIZE");
        Reader reader{process.value};
        for (const auto& anchor : {registry, names}) {
            std::vector<uint8_t> live(anchor.original.size());
            reader.read(base + anchor.instruction_rva, live.data(), live.size());
            require(live == anchor.original, "RUNTIME_ANCHOR_CHANGED");
        }
        const uint64_t pool = base + names.global_rva;
        require(read_name(reader, pool, 0) == "None", "NAME_ZERO_NOT_NONE");
        const auto array = reader.get<ArrayHeader>(base + registry.global_rva + 0x10);
        require(array.num_elements > 0 && array.num_elements <= array.max_elements &&
                array.max_elements <= 100000000 && array.num_chunks > 0 &&
                array.num_chunks <= array.max_chunks && array.max_chunks <= 8192 &&
                int64_t(array.num_chunks) * 65536 >= array.num_elements, "REGISTRY_COUNTS_INVALID");
        std::vector<uint64_t> chunks(array.num_chunks);
        reader.read(array.chunks, chunks.data(), chunks.size() * sizeof(uint64_t));
        auto item_at = [&](int32_t index) {
            require(index >= 0 && index < array.num_elements, "OBJECT_INDEX_OUT_OF_RANGE");
            return reader.get<ObjectItem>(chunks[uint32_t(index) >> 16] + uint64_t(index & 0xffff) * 24);
        };
        std::cout << "{\"event\":\"snapshot_start\",\"pid\":" << pid
                  << ",\"module_base\":" << quote(hex(base)) << ",\"sha256\":" << quote(fingerprint)
                  << ",\"registry_rva\":" << quote(hex(registry.global_rva))
                  << ",\"name_pool_rva\":" << quote(hex(names.global_rva))
                  << ",\"num_elements\":" << array.num_elements << ",\"num_chunks\":" << array.num_chunks << "}\n";
        uint32_t emitted = 0, null_slots = 0, changing_slots = 0;
        for (int32_t i = 0; i < array.num_elements && (!limit || emitted < limit); ++i) {
            auto item = item_at(i);
            if (!item.object) { ++null_slots; continue; }
            auto object = reader.get<ObjectHeader>(item.object);
            if (object.index != i || !object.cls) { ++changing_slots; continue; }
            auto cls = reader.get<ObjectHeader>(object.cls);
            require(item_at(cls.index).object == object.cls, "CLASS_NOT_REGISTERED");
            auto meta = reader.get<ObjectHeader>(cls.cls);
            require(item_at(meta.index).object == cls.cls, "METACLASS_NOT_REGISTERED");
            auto name = read_name(reader, pool, object.name_id, object.name_number);
            auto class_name = read_name(reader, pool, cls.name_id, cls.name_number);
            auto meta_name = read_name(reader, pool, meta.name_id, meta.name_number);
            auto again = item_at(i);
            auto object_again = reader.get<ObjectHeader>(item.object);
            if (again.object != item.object || again.serial != item.serial ||
                std::memcmp(&object, &object_again, sizeof(object)) != 0) { ++changing_slots; continue; }
            std::cout << "{\"event\":\"object\",\"index\":" << i << ",\"serial\":" << item.serial
                      << ",\"address\":" << quote(hex(item.object)) << ",\"name\":" << quote(name)
                      << ",\"class_name\":" << quote(class_name) << ",\"metaclass_name\":" << quote(meta_name)
                      << ",\"class_index\":" << cls.index << "}\n";
            ++emitted;
        }
        require(emitted != 0, "NO_VALID_OBJECTS");
        std::cout << "{\"event\":\"snapshot_end\",\"emitted\":" << emitted
                  << ",\"null_slots\":" << null_slots << ",\"changing_slots\":" << changing_slots << "}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "{\"event\":\"error\",\"message\":" << quote(error.what()) << "}\n";
        return 1;
    }
}
