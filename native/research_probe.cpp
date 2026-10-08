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
#include <unordered_set>
#include <unordered_map>
#include <functional>
#include <cmath>
#include <limits>
#include "stored_value_format.h"

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

std::vector<uint8_t> supported_image(const std::filesystem::path& path) {
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    require(bool(file), "MODULE_FILE_OPEN_FAILED");
    require(file.tellg() == 162421568, "UNSUPPORTED_BUILD_SIZE");
    std::vector<uint8_t> image(162421568); file.seekg(0);
    file.read(reinterpret_cast<char*>(image.data()), image.size());
    require(bool(file), "MODULE_FILE_READ_FAILED");
    const auto fingerprint = sha256(image);
    require(fingerprint == "218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618",
            "UNSUPPORTED_BUILD_SHA256=" + fingerprint);
    return image;
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

#include "thread_ping.h"
#include "fixed_observer_controller.h"
#include "session_controller.h"

int main(int argc, char** argv) {
    try {
        if (argc == 3 && std::string(argv[1]) == "--check-image") {
            // Exactly the startup fingerprint gate, without finding/attaching a process.
            supported_image(std::filesystem::path(argv[2]));
            std::cout << "{\"event\":\"build_supported\"}\n";
            return 0;
        }
        uint32_t limit = 32;
        std::string reflect_class;
        std::string bool_object;
        std::string function_owner, function_name;
        DWORD descriptor_pid = 0;
        bool read_values = false;
        std::unordered_map<int32_t, std::pair<int32_t, uint64_t>> descriptors;
        bool thread_ping = argc == 2 && std::string(argv[1]) == "--thread-ping";
        bool invoke_proof = argc == 2 && std::string(argv[1]) == "--invoke-proof";
        bool observe_proof = argc == 2 && std::string(argv[1]) == "--observe-proof";
        bool console_construction = argc == 2 && std::string(argv[1]) == "--console-construct-proof";
        bool runtime_session = argc == 2 && std::string(argv[1]) == "--session";
        bool catalog = argc == 2 && std::string(argv[1]) == "--catalog";
        if (catalog) limit = 0;
        if (invoke_proof || observe_proof || runtime_session || console_construction) limit = 0;
        int32_t proof_object = -1, proof_object_serial = 0, proof_function = -1, proof_function_serial = 0;
        if (argc == 3 && std::string(argv[1]) == "--limit") limit = std::stoul(argv[2]);
        else if (argc == 3 && std::string(argv[1]) == "--reflect-class") {
            reflect_class = argv[2]; limit = 0;
        }
        else if (argc == 3 && std::string(argv[1]) == "--read-bools") {
            bool_object = argv[2]; limit = 0;
        }
        else if (argc == 3 && std::string(argv[1]) == "--reflect-function") {
            std::string qualified = argv[2]; auto dot = qualified.rfind('.');
            require(dot != std::string::npos && dot > 0 && dot + 1 < qualified.size(),
                    "FUNCTION_NAME_REQUIRES_OWNER_DOT_NAME");
            function_owner = qualified.substr(0, dot); function_name = qualified.substr(dot + 1); limit = 0;
        }
        else if (argc == 4 && (std::string(argv[1]) == "--describe" || std::string(argv[1]) == "--read-values")) {
            read_values = std::string(argv[1]) == "--read-values";
            descriptor_pid = std::stoul(argv[2]);
            std::istringstream tokens(argv[3]); std::string token;
            while (std::getline(tokens, token, ',')) {
                auto first = token.find(':'), last = token.rfind(':');
                require(first != std::string::npos && last > first, "DESCRIPTOR_SELECTOR_INVALID");
                const auto index = std::stoi(token.substr(0, first));
                const auto serial = std::stoi(token.substr(first + 1, last - first - 1));
                const auto address = std::stoull(token.substr(last + 1), nullptr, 16);
                require(index >= 0 && descriptors.size() < 1024 &&
                        descriptors.emplace(index, std::make_pair(serial, address)).second,
                        "DESCRIPTOR_SELECTOR_DUPLICATE_OR_LIMIT");
            }
            require(!descriptors.empty(), "DESCRIPTOR_SELECTORS_EMPTY"); limit = 0;
        }
        else require(argc == 1 || catalog || thread_ping || invoke_proof || observe_proof || runtime_session || console_construction, "USAGE: research_probe.exe [--catalog | --limit N | --reflect-class NAME | --read-bools OBJECT | --reflect-function OWNER.NAME | --thread-ping | --invoke-proof | --observe-proof | --session]");
        const bool reflection = !reflect_class.empty() || !bool_object.empty() || !function_name.empty() || !descriptors.empty();
        DWORD pid = discover_process();
        require(descriptors.empty() || pid == descriptor_pid, "DESCRIPTOR_PROCESS_CHANGED");
        Handle process(OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid));
        require(process.value != nullptr, "OPEN_PROCESS_FAILED win32=" + std::to_string(GetLastError()));
        Handle snapshot(CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid));
        require(snapshot.value != INVALID_HANDLE_VALUE, "MODULE_SNAPSHOT_FAILED");
        MODULEENTRY32W module{}; module.dwSize = sizeof(module);
        require(Module32FirstW(snapshot.value, &module) != FALSE, "MODULE_NOT_FOUND");
        require(_wcsicmp(module.szModule, L"SandFall-Win64-Shipping.exe") == 0, "UNEXPECTED_MAIN_MODULE");
        auto image = supported_image(std::filesystem::path(module.szExePath));
        const std::string fingerprint = "218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618";
        auto registry = resolve_anchor(image, "48 8d 0d ?? ?? ?? ?? 48 8b d7 89 5c 24 20 44 8d 4b ff e8 ?? ?? ?? ?? 48 8b cf");
        auto names = resolve_anchor(image, "4c 8d 05 ?? ?? ?? ?? eb 16 48 8d 0d ?? ?? ?? ?? e8 ?? ?? ?? ?? 4c 8b c0 c6 05 ?? ?? ?? ?? 01 8b d3 0f b7 c3 c1 ea 10 89 44 24 44 89 54 24 40");
        require(registry.global_rva == 0x9361b60 && names.global_rva == 0x92aadc0,
                "DISCOVERY_DISAGREES_WITH_STATIC_EVIDENCE");
        const uint64_t base = reinterpret_cast<uint64_t>(module.modBaseAddr);
        require(module.modBaseSize == 166776832, "UNSUPPORTED_RUNTIME_IMAGE_SIZE");
        Reader reader{process.value};
        // Target thread-name and stack-report routines 141082dd0 / 14107b770
        // identify this build-scoped DWORD as GameThread's OS thread ID.
        DWORD game_thread = reader.get<DWORD>(base + 0x9272d30);
        Handle game_thread_handle(OpenThread(THREAD_QUERY_LIMITED_INFORMATION, FALSE, game_thread));
        require(game_thread_handle.value && GetProcessIdOfThread(game_thread_handle.value) == pid,
                "GAME_THREAD_ID_NOT_OWNED_BY_TARGET");
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
                  << ",\"game_thread_id\":" << game_thread
                  << ",\"module_base\":" << quote(hex(base)) << ",\"sha256\":" << quote(fingerprint)
                  << ",\"registry_rva\":" << quote(hex(registry.global_rva))
                  << ",\"registry_prefix_0\":" << reader.get<int32_t>(base + registry.global_rva)
                  << ",\"registry_prefix_4\":" << reader.get<int32_t>(base + registry.global_rva + 4)
                  << ",\"registry_prefix_8\":" << reader.get<int32_t>(base + registry.global_rva + 8)
                  << ",\"registry_prefix_c\":" << reader.get<uint32_t>(base + registry.global_rva + 12)
                  << ",\"name_pool_rva\":" << quote(hex(names.global_rva))
                  << ",\"num_elements\":" << array.num_elements << ",\"num_chunks\":" << array.num_chunks << "}\n";
        if (thread_ping) {
            run_thread_ping(pid, game_thread);
            std::cout << "{\"event\":\"snapshot_end\",\"emitted\":0}\n";
            return 0;
        }
        uint32_t emitted = 0, null_slots = 0, changing_slots = 0;
        auto derives_from_core_type = [&](uint64_t type, const std::string& wanted) {
            std::unordered_set<uint64_t> seen;
            bool found = false;
            while (type) {
                require(seen.size() < 128 && seen.insert(type).second, "TYPE_CHAIN_CYCLE_OR_LIMIT");
                const auto header = reader.get<ObjectHeader>(type);
                const auto slot = item_at(header.index);
                require(slot.object == type, "TYPE_NOT_REGISTERED");
                if (read_name(reader, pool, header.name_id, header.name_number) == wanted && header.outer) {
                    const auto package = reader.get<ObjectHeader>(header.outer);
                    require(item_at(package.index).object == header.outer, "TYPE_PACKAGE_NOT_REGISTERED");
                    found |= read_name(reader, pool, package.name_id, package.name_number) == "/Script/CoreUObject";
                }
                const auto parent = reader.get<uint64_t>(type + 0x40);
                const auto again = reader.get<ObjectHeader>(type);
                const auto slot_again = item_at(header.index);
                require(std::memcmp(&header, &again, sizeof(header)) == 0 &&
                        slot_again.object == type && slot_again.serial == slot.serial &&
                        reader.get<uint64_t>(type + 0x40) == parent, "TYPE_CHAIN_CHANGED");
                type = parent;
            }
            return found;
        };
        // UObject.Class and UStruct.SuperStruct are independently established for
        // this image. Record registered identities, not borrowed native handles.
        std::unordered_map<uint64_t, bool> catalog_classes;
        std::unordered_set<uint64_t> catalog_visiting;
        std::function<bool(uint64_t)> record_class = [&](uint64_t at) -> bool {
            if (!at) return false;
            auto known = catalog_classes.find(at);
            if (known != catalog_classes.end()) return known->second;
            require(catalog_visiting.size() < 128 && catalog_visiting.insert(at).second,
                    "CATALOG_CLASS_CYCLE_OR_LIMIT");
            const auto header = reader.get<ObjectHeader>(at);
            const auto slot = item_at(header.index);
            require(slot.object == at, "CATALOG_CLASS_NOT_REGISTERED");
            const auto parent = reader.get<uint64_t>(at + 0x40);
            const auto size = reader.get<int32_t>(at + 0x58);
            const auto name = read_name(reader, pool, header.name_id, header.name_number);
            // Metaclass default objects (observed Default__Class) may have a
            // zero-sized uninitialized descriptor. Catalog it, but do not infer
            // that it describes readable UObject instance storage.
            require(size >= 0 && size <= 16 * 1024 * 1024,
                    "CATALOG_CLASS_SIZE_INVALID name=" + name + " index=" +
                    std::to_string(header.index) + " size=" + std::to_string(size));
            const bool parent_is_metaclass = record_class(parent);
            const bool is_metaclass = (name == "Class" && header.cls == at) || parent_is_metaclass;
            int32_t parent_index = -1;
            if (parent) parent_index = reader.get<ObjectHeader>(parent).index;
            const auto again = reader.get<ObjectHeader>(at);
            const auto slot_again = item_at(header.index);
            require(slot_again.object == at && slot_again.serial == slot.serial &&
                    std::memcmp(&header, &again, sizeof(header)) == 0 &&
                    reader.get<uint64_t>(at + 0x40) == parent &&
                    reader.get<int32_t>(at + 0x58) == size, "CATALOG_CLASS_CHANGED");
            std::cout << "{\"event\":\"class_relation\",\"index\":" << header.index
                      << ",\"serial\":" << slot.serial << ",\"name\":" << quote(name)
                      << ",\"super_index\":" << parent_index << ",\"size\":" << size << "}\n";
            catalog_visiting.erase(at);
            catalog_classes.emplace(at, is_metaclass);
            return is_metaclass;
        };
        for (int32_t i = 0; i < array.num_elements && (!limit || emitted < limit); ++i) {
            if (!descriptors.empty() && descriptors.find(i) == descriptors.end()) continue;
            auto item = item_at(i);
            if (!descriptors.empty()) {
                const auto expected = descriptors.at(i);
                require(item.serial == expected.first && item.object == expected.second,
                        "DESCRIPTOR_IDENTITY_CHANGED");
            }
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
            bool descriptor_function = false;
            if (!descriptors.empty() && !read_values) {
                // Validate UStruct membership through the observed metaclass chain;
                // never reinterpret arbitrary UObject bytes as reflection metadata.
                std::unordered_set<uint64_t> seen_types;
                bool is_struct = false;
                for (uint64_t type = object.cls; type;) {
                    require(seen_types.size() < 128 && seen_types.insert(type).second,
                            "DESCRIPTOR_TYPE_CYCLE_OR_LIMIT");
                    const auto header = reader.get<ObjectHeader>(type);
                    const auto slot = item_at(header.index);
                    require(slot.object == type, "DESCRIPTOR_TYPE_NOT_REGISTERED");
                    const auto type_name = read_name(reader, pool, header.name_id, header.name_number);
                    if (header.outer && (type_name == "Struct" || type_name == "Function")) {
                        const auto package = reader.get<ObjectHeader>(header.outer);
                        require(item_at(package.index).object == header.outer, "DESCRIPTOR_PACKAGE_NOT_REGISTERED");
                        if (read_name(reader, pool, package.name_id, package.name_number) == "/Script/CoreUObject") {
                            is_struct |= type_name == "Struct";
                            descriptor_function |= type_name == "Function";
                        }
                    }
                    const auto parent = reader.get<uint64_t>(type + 0x40);
                    const auto again = reader.get<ObjectHeader>(type);
                    require(std::memcmp(&header, &again, sizeof(header)) == 0 &&
                            item_at(header.index).serial == slot.serial, "DESCRIPTOR_TYPE_CHANGED");
                    type = parent;
                }
                require(is_struct, "DESCRIPTOR_TARGET_NOT_STRUCT");
            }
            int32_t outer_index = -1, outer_serial = 0;
            if (catalog) {
                if (record_class(object.cls)) record_class(item.object);
                if (object.outer) {
                    const auto outer = reader.get<ObjectHeader>(object.outer);
                    const auto outer_item = item_at(outer.index);
                    const auto outer_again = reader.get<ObjectHeader>(object.outer);
                    require(outer_item.object == object.outer &&
                            std::memcmp(&outer, &outer_again, sizeof(outer)) == 0,
                            "CATALOG_OUTER_CHANGED");
                    outer_index = outer.index; outer_serial = outer_item.serial;
                }
            }
            if (invoke_proof || observe_proof || runtime_session || console_construction) {
                if (name == "Default__Actor" && class_name == "Actor") {
                    require(proof_object == -1, "AMBIGUOUS_PROOF_OBJECT"); proof_object = i; proof_object_serial = item.serial;
                } else if (name == "IsActorBeingDestroyed" && class_name == "Function") {
                    auto outer = reader.get<ObjectHeader>(object.outer);
                    require(item_at(outer.index).object == object.outer, "PROOF_FUNCTION_OWNER_INVALID");
                    if (read_name(reader, pool, outer.name_id, outer.name_number) != "Actor") continue;
                    require(proof_function == -1, "AMBIGUOUS_PROOF_FUNCTION"); proof_function = i; proof_function_serial = item.serial;
                } else continue;
            }
            if (!reflect_class.empty() && (name != reflect_class || class_name != "Class")) continue;
            if (!bool_object.empty() && name != bool_object) continue;
            if (!function_name.empty()) {
                if (name != function_name || class_name != "Function") continue;
                auto outer = reader.get<ObjectHeader>(object.outer);
                require(item_at(outer.index).object == object.outer, "FUNCTION_OWNER_NOT_REGISTERED");
                if (read_name(reader, pool, outer.name_id, outer.name_number) != function_owner) continue;
            }
            if (!bool_object.empty()) require(meta_name == "Class", "NATIVE_OBJECT_REQUIRED");
            if (reflection && descriptors.empty()) require(emitted == 0, "AMBIGUOUS_QUERY_NAME");
            auto again = item_at(i);
            auto object_again = reader.get<ObjectHeader>(item.object);
            if (again.object != item.object || again.serial != item.serial ||
                std::memcmp(&object, &object_again, sizeof(object)) != 0) { ++changing_slots; continue; }
            std::cout << "{\"event\":\"object\",\"index\":" << i << ",\"serial\":" << item.serial
                      << ",\"address\":" << quote(hex(item.object)) << ",\"name\":" << quote(name)
                      << ",\"object_flags\":" << quote(hex(object.flags)) << ",\"item_flags\":" << quote(hex(item.flags))
                      << ",\"class_name\":" << quote(class_name) << ",\"metaclass_name\":" << quote(meta_name)
                      << ",\"class_index\":" << cls.index;
            if (catalog) std::cout << ",\"outer_index\":" << outer_index
                                  << ",\"outer_serial\":" << outer_serial;
            if (reflection) {
                // Candidate slot corroborated by two name-lookup callers.
                // Expose research evidence only; never invoke it here.
                auto dispatch = reader.get<uint64_t>(object.vtable + 0x268);
                require(dispatch >= base && dispatch < base + module.modBaseSize,
                        "DISPATCH_CANDIDATE_OUTSIDE_MODULE");
                std::cout << ",\"vtable_rva\":" << quote(hex(object.vtable - base))
                          << ",\"dispatch_candidate_rva\":" << quote(hex(dispatch - base));
            }
            std::cout << "}\n";
            ++emitted;
            if (!function_name.empty() || descriptor_function) {
                auto reported_owner = function_owner;
                if (descriptor_function) {
                    const auto outer = reader.get<ObjectHeader>(object.outer);
                    require(item_at(outer.index).object == object.outer, "FUNCTION_OWNER_NOT_REGISTERED");
                    reported_owner = read_name(reader, pool, outer.name_id, outer.name_number);
                }
                uint32_t flags = reader.get<uint32_t>(item.object + 0xb0);
                uint16_t params_size = reader.get<uint16_t>(item.object + 0xb6);
                uint16_t return_offset = reader.get<uint16_t>(item.object + 0xb8);
                uint64_t entry = reader.get<uint64_t>(item.object + 0xd8);
                require(entry >= base && entry < base + module.modBaseSize, "FUNCTION_ENTRY_OUTSIDE_MODULE");
                std::cout << "{\"event\":\"function_metadata\",\"owner\":" << quote(reported_owner)
                          << ",\"flags\":" << quote(hex(flags)) << ",\"params_size\":" << params_size
                          << ",\"return_offset\":" << return_offset
                          << ",\"entry_rva\":" << quote(hex(entry - base)) << "}\n";
            }
            if (reflection) {
                // Derived from target routines 1412792f0, 1412813d0, 14134c3b0,
                // 1412ab240 and 1412aca00. Research metadata, not callable handles.
                uint64_t owner = bool_object.empty() && !read_values ? item.object : object.cls;
                std::unordered_set<uint64_t> owners;
                while (owner) {
                    require(owners.size() < 128 && owners.insert(owner).second, "CLASS_CHAIN_CYCLE_OR_LIMIT");
                    auto header = reader.get<ObjectHeader>(owner);
                    auto owner_item = item_at(header.index);
                    require(owner_item.object == owner, "REFLECTION_OWNER_NOT_REGISTERED");
                    auto owner_name = read_name(reader, pool, header.name_id, header.name_number);
                    uint64_t super = reader.get<uint64_t>(owner + 0x40);
                    uint64_t first = reader.get<uint64_t>(owner + 0x50);
                    int32_t size = reader.get<int32_t>(owner + 0x58);
                    require(size >= (function_name.empty() && descriptors.empty() ? 40 : 0) && size <= 16 * 1024 * 1024, "STRUCT_SIZE_INVALID");
                    std::cout << "{\"event\":" << quote(function_name.empty() && descriptors.empty() ? "class_metadata" : "struct_metadata") << ",\"name\":" << quote(owner_name)
                              << ",\"index\":" << header.index << ",\"size\":" << size
                              << ",\"serial\":" << owner_item.serial << ",\"address\":" << quote(hex(owner))
                              << ",\"super\":" << quote(hex(super)) << "}\n";
                    std::unordered_set<uint64_t> fields;
                    for (uint64_t field = first; field;) {
                        require(fields.size() < 4096 && fields.insert(field).second, "FIELD_CHAIN_CYCLE_OR_LIMIT");
                        struct PropertyPrefix {
                            uint64_t vtable, type, owner, next;
                            uint32_t name_id, number, field_flags, pad;
                            int32_t dimension, element_size;
                            uint64_t flags;
                            uint32_t rep_info; int32_t offset;
                        };
                        static_assert(sizeof(PropertyPrefix) == 0x48);
                        auto p = reader.get<PropertyPrefix>(field);
                        require((p.owner & 1) && (p.owner & ~1ULL) == owner, "FIELD_OWNER_MISMATCH");
                        require((reader.get<uint64_t>(p.type + 0x10) & 0x8000) != 0, "FIELD_NOT_PROPERTY");
                        auto type_name = reader.get<uint64_t>(p.type);
                        require(p.dimension > 0 && p.element_size > 0 && p.offset >= 0 &&
                                int64_t(p.offset) + int64_t(p.dimension) * p.element_size <= size,
                                "PROPERTY_EXTENT_INVALID");
                        auto field_name = read_name(reader, pool, p.name_id, p.number);
                        auto type = read_name(reader, pool, uint32_t(type_name), uint32_t(type_name >> 32));
                        auto p_again = reader.get<PropertyPrefix>(field);
                        require(std::memcmp(&p, &p_again, sizeof(p)) == 0, "PROPERTY_CHANGED");
                        std::cout << "{\"event\":\"property_metadata\",\"owner\":" << quote(owner_name)
                                  << ",\"owner_index\":" << header.index
                                  << ",\"name\":" << quote(field_name) << ",\"type\":" << quote(type)
                                  << ",\"offset\":" << p.offset << ",\"element_size\":" << p.element_size
                                  << ",\"dimension\":" << p.dimension << ",\"flags\":" << quote(hex(p.flags));
                        if (p.vtable >= base && p.vtable < base + module.modBaseSize)
                            std::cout << ",\"vtable_rva\":" << quote(hex(p.vtable - base));
                        if (type == "BoolProperty") {
                            std::cout << ",\"bool_encoding\":" << quote(hex(reader.get<uint32_t>(field + 0x70)));
                        }
                        // Target virtual type paths 14136f810 / 1412aa430 /
                        // 14136e840 and child traversal 14133f630 / 1412abb90.
                        // Metadata only; do not treat these pointers as lasting handles.
                        if (type == "StructProperty" || type == "EnumProperty" || type == "ByteProperty") {
                            const auto reference_offset = type == "EnumProperty" ? 0x78 : 0x70;
                            const auto reference = reader.get<uint64_t>(field + reference_offset);
                            require(reference || type == "ByteProperty", "PROPERTY_TYPE_REFERENCE_NULL");
                            if (reference) {
                                const auto target = reader.get<ObjectHeader>(reference);
                                const auto target_item = item_at(target.index);
                                require(target_item.object == reference, "PROPERTY_TYPE_NOT_REGISTERED");
                                require(derives_from_core_type(target.cls, type == "StructProperty" ? "ScriptStruct" : "Enum"),
                                        "PROPERTY_TYPE_CLASS_MISMATCH");
                                const auto target_name = read_name(reader, pool, target.name_id, target.name_number);
                                const auto target_again = reader.get<ObjectHeader>(reference);
                                const auto item_again = item_at(target.index);
                                require(std::memcmp(&target, &target_again, sizeof(target)) == 0 &&
                                        item_again.object == reference && item_again.serial == target_item.serial &&
                                        reader.get<uint64_t>(field + reference_offset) == reference,
                                        "PROPERTY_TYPE_CHANGED");
                                std::cout << (type == "StructProperty" ? ",\"struct_name\":" : ",\"enum_name\":")
                                          << quote(target_name)
                                          << (type == "StructProperty" ? ",\"struct_index\":" : ",\"enum_index\":")
                                          << target.index
                                          << (type == "StructProperty" ? ",\"struct_serial\":" : ",\"enum_serial\":")
                                          << target_item.serial;
                            }
                        }
                        // Target type-name virtuals: 14136e440 reads the class
                        // at +70; 14136ea40 reads the class constraint at +78.
                        // Multicast type formatting 14136f160 reads a nullable
                        // signature UObject at +70. Validate live metatypes too.
                        const bool object_type = type == "ObjectProperty" || type == "WeakObjectProperty";
                        const bool class_type = type == "ClassProperty" || type == "SoftClassProperty";
                        const bool delegate_type = type == "MulticastInlineDelegateProperty" ||
                                                   type == "MulticastSparseDelegateProperty";
                        if (object_type || class_type || delegate_type) {
                            const auto reference_offset = class_type ? 0x78 : 0x70;
                            const auto reference = reader.get<uint64_t>(field + reference_offset);
                            require(reference || delegate_type, "PROPERTY_REFERENCE_NULL");
                            if (reference) {
                                const auto target = reader.get<ObjectHeader>(reference);
                                const auto target_item = item_at(target.index);
                                require(target_item.object == reference, "PROPERTY_REFERENCE_NOT_REGISTERED");
                                require(derives_from_core_type(target.cls, delegate_type ? "Function" : "Class"),
                                        "PROPERTY_REFERENCE_CLASS_MISMATCH");
                                const auto target_name = read_name(reader, pool, target.name_id, target.name_number);
                                const auto target_again = reader.get<ObjectHeader>(reference);
                                const auto item_again = item_at(target.index);
                                require(std::memcmp(&target, &target_again, sizeof(target)) == 0 &&
                                        item_again.object == reference && item_again.serial == target_item.serial &&
                                        reader.get<uint64_t>(field + reference_offset) == reference,
                                        "PROPERTY_REFERENCE_CHANGED");
                                const std::string prefix = delegate_type ? "signature_function" :
                                                           class_type ? "meta_class" : "property_class";
                                std::cout << "," << quote(prefix + "_name") << ":" << quote(target_name)
                                          << "," << quote(prefix + "_index") << ":" << target.index
                                          << "," << quote(prefix + "_serial") << ":" << target_item.serial
                                          << "," << quote(prefix + "_address") << ":" << quote(hex(reference));
                            }
                        }
                        if (type == "ArrayProperty" || type == "EnumProperty") {
                            const auto inner_offset = type == "ArrayProperty" ? 0x78 : 0x70;
                            const auto inner = reader.get<uint64_t>(field + inner_offset);
                            require(inner && inner != field, "INNER_PROPERTY_INVALID");
                            const auto child = reader.get<PropertyPrefix>(inner);
                            require(child.owner == field && child.dimension == 1 && child.offset == 0 &&
                                    child.element_size > 0 && child.element_size <= 16 * 1024 * 1024 &&
                                    (reader.get<uint64_t>(child.type + 0x10) & 0x8000),
                                    "INNER_PROPERTY_LAYOUT_INVALID");
                            const auto child_type = reader.get<uint64_t>(child.type);
                            const auto child_name = read_name(reader, pool, uint32_t(child_type), uint32_t(child_type >> 32));
                            const auto child_field_name = read_name(reader, pool, child.name_id, child.number);
                            const auto child_again = reader.get<PropertyPrefix>(inner);
                            require(std::memcmp(&child, &child_again, sizeof(child)) == 0 &&
                                    reader.get<uint64_t>(field + inner_offset) == inner, "INNER_PROPERTY_CHANGED");
                            std::cout << ",\"inner_type\":" << quote(child_name)
                                      << ",\"inner_name\":" << quote(child_field_name)
                                      << ",\"inner_element_size\":" << child.element_size;
                        }
                        std::cout << "}\n";
                        const auto scalar_json = [&](const std::string& value_type, uint64_t raw) {
                            std::ostringstream value;
                            if (value_type == "FloatProperty") {
                                float number; std::memcpy(&number, &raw, 4);
                                value << stored_float_json(number);
                            } else if (value_type == "DoubleProperty") {
                                double number; std::memcpy(&number, &raw, 8);
                                value << stored_float_json(number);
                            } else if (value_type == "IntProperty") value << static_cast<int32_t>(raw);
                            else if (value_type == "UInt16Property") value << static_cast<uint16_t>(raw);
                            else if (value_type == "ByteProperty") value << static_cast<unsigned>(static_cast<uint8_t>(raw));
                            else if (value_type == "NameProperty") value << quote(read_name(reader, pool, uint32_t(raw), uint32_t(raw >> 32)));
                            else {
                                require(value_type == "ObjectProperty", "SCALAR_TYPE_UNSUPPORTED");
                                if (!raw) value << "null";
                                else {
                                    const auto target = reader.get<ObjectHeader>(raw);
                                    const auto slot = item_at(target.index);
                                    require(slot.object == raw, "VALUE_REFERENCE_NOT_REGISTERED");
                                    const auto target_name = read_name(reader, pool, target.name_id, target.name_number);
                                    const auto target_again = reader.get<ObjectHeader>(raw);
                                    const auto slot_again = item_at(target.index);
                                    require(slot_again.object == raw && slot_again.serial == slot.serial &&
                                        std::memcmp(&target, &target_again, sizeof(target)) == 0, "VALUE_REFERENCE_CHANGED");
                                    value << "{\"$reference\":{\"index\":" << target.index << ",\"serial\":" << slot.serial
                                          << ",\"address\":" << quote(hex(raw)) << ",\"name\":" << quote(target_name) << "}}";
                                }
                            }
                            return value.str();
                        };
                        const auto scalar_width = [](const std::string& value_type) {
                            return value_type == "FloatProperty" || value_type == "IntProperty" ? 4 :
                                value_type == "UInt16Property" ? 2 : value_type == "ByteProperty" ? 1 :
                                value_type == "NameProperty" || value_type == "ObjectProperty" || value_type == "DoubleProperty" ? 8 : 0;
                        };
                        if (read_values && type == "ArrayProperty") {
                            try {
                                // Target export 14133c540: flags +70, child +78,
                                // data +0/count +8. Copy 14133a6f0 checks capacity
                                // at +c; 14133c010 strides by child ElementSize.
                                // Relative/frozen allocator storage is not decoded.
                                struct ArrayHeader { uint64_t data; int32_t count, capacity; };
                                static_assert(sizeof(ArrayHeader) == 16);
                                const auto array_flags = reader.get<uint8_t>(field + 0x70);
                                require((array_flags & 1) == 0, "ARRAY_ALLOCATOR_UNSUPPORTED");
                                require(p.element_size == 16 && p.dimension <= 1024, "ARRAY_PROPERTY_LAYOUT_INVALID");
                                const auto inner = reader.get<uint64_t>(field + 0x78);
                                require(inner && inner != field, "ARRAY_INNER_INVALID");
                                const auto child = reader.get<PropertyPrefix>(inner);
                                const auto child_id = reader.get<uint64_t>(child.type);
                                const auto child_type = read_name(reader, pool, uint32_t(child_id), uint32_t(child_id >> 32));
                                const auto width = scalar_width(child_type);
                                require(width != 0, "ARRAY_ELEMENT_TYPE_UNSUPPORTED");
                                require(child.owner == field && child.dimension == 1 && child.offset == 0 &&
                                        child.element_size == width && (reader.get<uint64_t>(child.type + 0x10) & 0x8000),
                                        "ARRAY_INNER_LAYOUT_INVALID");
                                for (int32_t element = 0; element < p.dimension; ++element) {
                                    const auto at = item.object + p.offset + uint64_t(element) * 16;
                                    const auto observed_array = reader.get<ArrayHeader>(at);
                                    require(observed_array.count >= 0 && observed_array.count <= observed_array.capacity && observed_array.capacity <= 1048576,
                                            "ARRAY_COUNTS_INVALID");
                                    const auto copied = std::min(observed_array.count, 64);
                                    std::vector<uint8_t> bytes(size_t(copied) * width), repeated(bytes.size());
                                    if (copied) {
                                        require(observed_array.data && (observed_array.data & 1) == 0, "ARRAY_DATA_INVALID");
                                        reader.read(observed_array.data, bytes.data(), bytes.size());
                                    }
                                    std::ostringstream values;
                                    for (int32_t index = 0; index < copied; ++index) {
                                        uint64_t raw = 0;
                                        std::memcpy(&raw, bytes.data() + size_t(index) * width, width);
                                        if (index) values << ',';
                                        values << scalar_json(child_type, raw);
                                    }
                                    if (copied) reader.read(observed_array.data, repeated.data(), repeated.size());
                                    const auto array_again = reader.get<ArrayHeader>(at);
                                    const auto child_again = reader.get<PropertyPrefix>(inner);
                                    const auto property_again = reader.get<PropertyPrefix>(field);
                                    require(bytes == repeated && std::memcmp(&observed_array, &array_again, sizeof(observed_array)) == 0 &&
                                            std::memcmp(&child, &child_again, sizeof(child)) == 0 &&
                                            std::memcmp(&p, &property_again, sizeof(p)) == 0 &&
                                            reader.get<uint64_t>(field + 0x78) == inner &&
                                            reader.get<uint8_t>(field + 0x70) == array_flags, "ARRAY_OBSERVATION_CHANGED");
                                    std::cout << "{\"event\":\"stored_value\",\"owner_index\":" << header.index
                                              << ",\"name\":" << quote(field_name) << ",\"element\":" << element
                                              << ",\"value\":{\"$array\":{\"length\":" << observed_array.count
                                              << ",\"items\":[" << values.str() << "]}},\"truncated\":"
                                              << (observed_array.count > copied ? "true" : "false") << "}\n";
                                }
                            } catch (const std::exception& error) {
                                std::cout << "{\"event\":\"stored_value_error\",\"owner_index\":" << header.index
                                          << ",\"name\":" << quote(field_name) << ",\"error\":" << quote(error.what()) << "}\n";
                            }
                        }
                        if (read_values && type != "BoolProperty") {
                            // Target exports: 14136b3e0 -> numeric vt+200,
                            // 141370ac0 float, 141370a60 signed32, 141370a30
                            // unsigned16; 14136a290 byte; 14136b200 FName;
                            // 14133c740 stored object reference. No custom getters.
                            const int width = scalar_width(type);
                            if (width) {
                                try {
                                    require(p.element_size == width && p.dimension <= 1024, "VALUE_LAYOUT_INVALID");
                                    for (int32_t element = 0; element < p.dimension; ++element) {
                                        const auto at = item.object + p.offset + uint64_t(element) * width;
                                        uint64_t raw = 0, value_again = 0;
                                        reader.read(at, &raw, width);
                                        const auto value = scalar_json(type, raw);
                                        reader.read(at, &value_again, width);
                                        const auto property_again = reader.get<PropertyPrefix>(field);
                                        require(raw == value_again && std::memcmp(&p, &property_again, sizeof(p)) == 0, "STORED_VALUE_CHANGED");
                                        std::cout << "{\"event\":\"stored_value\",\"owner_index\":" << header.index
                                                  << ",\"name\":" << quote(field_name) << ",\"element\":" << element
                                                  << ",\"value\":" << value << "}\n";
                                    }
                                } catch (const std::exception& error) {
                                    std::cout << "{\"event\":\"stored_value_error\",\"owner_index\":" << header.index
                                              << ",\"name\":" << quote(field_name) << ",\"error\":" << quote(error.what()) << "}\n";
                                }
                            }
                        }
                        if (read_values && type == "StrProperty") {
                            try {
                                struct StringHeader { uint64_t data; int32_t count, capacity; };
                                static_assert(sizeof(StringHeader) == 16);
                                require(p.element_size == 16 && p.dimension <= 1024, "STRING_PROPERTY_LAYOUT_INVALID");
                                for (int32_t element = 0; element < p.dimension; ++element) {
                                    const auto at = item.object + p.offset + uint64_t(element) * 16;
                                    const auto text = reader.get<StringHeader>(at);
                                    require(text.count >= 0 && text.count <= text.capacity && text.capacity <= 1048576,
                                            "STRING_COUNTS_INVALID");
                                    const auto units = std::min(text.count, 8193);
                                    std::wstring wide(units, 0), repeated(units, 0);
                                    if (units) {
                                        reader.read(text.data, wide.data(), units * 2);
                                        reader.read(text.data, repeated.data(), units * 2);
                                        require(wide == repeated, "STRING_CONTENT_CHANGED");
                                    }
                                    const auto text_again = reader.get<StringHeader>(at);
                                    const auto property_again = reader.get<PropertyPrefix>(field);
                                    require(std::memcmp(&text, &text_again, sizeof(text)) == 0 &&
                                            std::memcmp(&p, &property_again, sizeof(p)) == 0, "STRING_HEADER_CHANGED");
                                    if (text.count && text.count <= 8193) {
                                        require(wide.back() == 0, "STRING_TERMINATOR_INVALID");
                                        wide.pop_back();
                                    } else if (wide.size() > 8192) wide.resize(8192);
                                    // A bounded prefix must not end halfway through a surrogate pair.
                                    if (text.count > 8193 && !wide.empty() && wide.back() >= 0xd800 && wide.back() <= 0xdbff)
                                        wide.pop_back();
                                    std::string decoded;
                                    if (!wide.empty()) {
                                        const auto bytes = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, wide.data(),
                                            static_cast<int>(wide.size()), nullptr, 0, nullptr, nullptr);
                                        require(bytes > 0, "STRING_UTF16_INVALID"); decoded.resize(bytes);
                                        WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, wide.data(),
                                            static_cast<int>(wide.size()), decoded.data(), bytes, nullptr, nullptr);
                                    }
                                    std::cout << "{\"event\":\"stored_value\",\"owner_index\":" << header.index
                                              << ",\"name\":" << quote(field_name) << ",\"element\":" << element
                                              << ",\"value\":" << quote(decoded) << ",\"truncated\":"
                                              << (text.count > 8193 ? "true" : "false") << "}\n";
                                }
                            } catch (const std::exception& error) {
                                std::cout << "{\"event\":\"stored_value_error\",\"owner_index\":" << header.index
                                          << ",\"name\":" << quote(field_name) << ",\"error\":" << quote(error.what()) << "}\n";
                            }
                        }
                        if ((!bool_object.empty() || read_values) && type == "BoolProperty") {
                            try {
                            // Target export routine 14136a160 confirms this stored-value
                            // truth test; this does not call custom property accessors.
                            const uint32_t encoding = reader.get<uint32_t>(field + 0x70);
                            const uint8_t byte_offset = uint8_t(encoding >> 8);
                            const uint8_t mask = uint8_t(encoding >> 24);
                            require(mask && byte_offset < p.element_size &&
                                    p.dimension <= 1024, "BOOL_ENCODING_INVALID");
                            for (int32_t element = 0; element < p.dimension; ++element) {
                                uint64_t at = item.object + p.offset +
                                              uint64_t(element) * p.element_size + byte_offset;
                                uint8_t raw = reader.get<uint8_t>(at);
                                require(reader.get<uint8_t>(at) == raw &&
                                        reader.get<uint32_t>(field + 0x70) == encoding,
                                        "BOOL_OBSERVATION_CHANGED");
                                std::cout << "{\"event\":\"stored_bool\",\"owner\":" << quote(owner_name)
                                          << ",\"owner_index\":" << header.index
                                          << ",\"name\":" << quote(field_name) << ",\"element\":" << element
                                          << ",\"value\":" << ((raw & mask) ? "true" : "false")
                                          << ",\"raw_byte\":" << unsigned(raw) << ",\"mask\":" << unsigned(mask)
                                          << ",\"byte_offset\":" << unsigned(byte_offset) << "}\n";
                            }
                            } catch (const std::exception& error) {
                                if (!read_values) throw;
                                std::cout << "{\"event\":\"stored_value_error\",\"owner_index\":" << header.index
                                          << ",\"name\":" << quote(field_name) << ",\"error\":" << quote(error.what()) << "}\n";
                            }
                        }
                        field = p.next;
                    }
                    auto owner_again = item_at(header.index);
                    require(owner_again.object == owner && owner_again.serial == owner_item.serial &&
                            reader.get<uint64_t>(owner + 0x40) == super &&
                            reader.get<uint64_t>(owner + 0x50) == first, "REFLECTION_OWNER_CHANGED");
                    owner = super;
                }
                auto final_item = item_at(i);
                auto final_header = reader.get<ObjectHeader>(item.object);
                require(final_item.object == item.object && final_item.serial == item.serial &&
                        std::memcmp(&final_header, &object, sizeof(object)) == 0,
                        "REFLECTION_TARGET_CHANGED");
            }
        }
        require(emitted != 0, "NO_VALID_OBJECTS");
        require(descriptors.empty() || emitted == descriptors.size(), "DESCRIPTOR_SET_INCOMPLETE");
        if (invoke_proof || observe_proof || runtime_session || console_construction) {
            require(proof_object >= 0 && proof_function >= 0 && emitted == 2, "PROOF_TARGETS_MISSING_OR_UNSTABLE");
            if (runtime_session) run_runtime_session(pid, game_thread, proof_object, proof_object_serial, proof_function, proof_function_serial);
            else if (observe_proof) run_fixed_observer(pid, game_thread, proof_object, proof_object_serial, proof_function, proof_function_serial);
            else run_thread_ping(pid, game_thread, console_construction ? 2 : 1, proof_object, proof_object_serial, proof_function, proof_function_serial);
        }
        std::cout << "{\"event\":\"snapshot_end\",\"emitted\":" << emitted
                  << ",\"null_slots\":" << null_slots << ",\"changing_slots\":" << changing_slots << "}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "{\"event\":\"error\",\"message\":" << quote(error.what()) << "}\n";
        return 1;
    }
}

