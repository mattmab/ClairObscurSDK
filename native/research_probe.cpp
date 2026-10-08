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

#include "thread_ping.h"

int main(int argc, char** argv) {
    try {
        uint32_t limit = 32;
        std::string reflect_class;
        std::string bool_object;
        std::string function_owner, function_name;
        bool thread_ping = argc == 2 && std::string(argv[1]) == "--thread-ping";
        bool invoke_proof = argc == 2 && std::string(argv[1]) == "--invoke-proof";
        if (invoke_proof) limit = 0;
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
        else require(argc == 1 || thread_ping || invoke_proof, "USAGE: research_probe.exe [--limit N | --reflect-class NAME | --read-bools OBJECT | --reflect-function OWNER.NAME | --thread-ping | --invoke-proof]");
        const bool reflection = !reflect_class.empty() || !bool_object.empty() || !function_name.empty();
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
                  << ",\"name_pool_rva\":" << quote(hex(names.global_rva))
                  << ",\"num_elements\":" << array.num_elements << ",\"num_chunks\":" << array.num_chunks << "}\n";
        if (thread_ping) {
            run_thread_ping(pid, game_thread);
            std::cout << "{\"event\":\"snapshot_end\",\"emitted\":0}\n";
            return 0;
        }
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
            if (invoke_proof) {
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
            if (reflection) require(emitted == 0, "AMBIGUOUS_QUERY_NAME");
            auto again = item_at(i);
            auto object_again = reader.get<ObjectHeader>(item.object);
            if (again.object != item.object || again.serial != item.serial ||
                std::memcmp(&object, &object_again, sizeof(object)) != 0) { ++changing_slots; continue; }
            std::cout << "{\"event\":\"object\",\"index\":" << i << ",\"serial\":" << item.serial
                      << ",\"address\":" << quote(hex(item.object)) << ",\"name\":" << quote(name)
                      << ",\"class_name\":" << quote(class_name) << ",\"metaclass_name\":" << quote(meta_name)
                      << ",\"class_index\":" << cls.index;
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
            if (!function_name.empty()) {
                uint32_t flags = reader.get<uint32_t>(item.object + 0xb0);
                uint16_t params_size = reader.get<uint16_t>(item.object + 0xb6);
                uint16_t return_offset = reader.get<uint16_t>(item.object + 0xb8);
                uint64_t entry = reader.get<uint64_t>(item.object + 0xd8);
                require(entry >= base && entry < base + module.modBaseSize, "FUNCTION_ENTRY_OUTSIDE_MODULE");
                std::cout << "{\"event\":\"function_metadata\",\"owner\":" << quote(function_owner)
                          << ",\"flags\":" << quote(hex(flags)) << ",\"params_size\":" << params_size
                          << ",\"return_offset\":" << return_offset
                          << ",\"entry_rva\":" << quote(hex(entry - base)) << "}\n";
            }
            if (reflection) {
                // Derived from target routines 1412792f0, 1412813d0, 14134c3b0,
                // 1412ab240 and 1412aca00. Research metadata, not callable handles.
                uint64_t owner = bool_object.empty() ? item.object : object.cls;
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
                    require(size >= (function_name.empty() ? 40 : 0) && size <= 16 * 1024 * 1024, "STRUCT_SIZE_INVALID");
                    std::cout << "{\"event\":" << quote(function_name.empty() ? "class_metadata" : "struct_metadata") << ",\"name\":" << quote(owner_name)
                              << ",\"index\":" << header.index << ",\"size\":" << size
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
                                  << ",\"name\":" << quote(field_name) << ",\"type\":" << quote(type)
                                  << ",\"offset\":" << p.offset << ",\"element_size\":" << p.element_size
                                  << ",\"dimension\":" << p.dimension << ",\"flags\":" << quote(hex(p.flags));
                        if (type == "BoolProperty") {
                            std::cout << ",\"bool_encoding\":" << quote(hex(reader.get<uint32_t>(field + 0x70)));
                        }
                        std::cout << "}\n";
                        if (!bool_object.empty() && type == "BoolProperty") {
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
                                          << ",\"name\":" << quote(field_name) << ",\"element\":" << element
                                          << ",\"value\":" << ((raw & mask) ? "true" : "false")
                                          << ",\"raw_byte\":" << unsigned(raw) << ",\"mask\":" << unsigned(mask)
                                          << ",\"byte_offset\":" << unsigned(byte_offset) << "}\n";
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
        if (invoke_proof) {
            require(proof_object >= 0 && proof_function >= 0 && emitted == 2, "PROOF_TARGETS_MISSING_OR_UNSTABLE");
            run_thread_ping(pid, game_thread, 1, proof_object, proof_object_serial, proof_function, proof_function_serial);
        }
        std::cout << "{\"event\":\"snapshot_end\",\"emitted\":" << emitted
                  << ",\"null_slots\":" << null_slots << ",\"changing_slots\":" << changing_slots << "}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "{\"event\":\"error\",\"message\":" << quote(error.what()) << "}\n";
        return 1;
    }
}
