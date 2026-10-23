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
#include "session_specimen_filter.h"
#include "reader_session.h"

int run_query(int argc, char** argv) {
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
        bool read_values = false, read_enums = false, read_script = false, read_table = false;
        std::unordered_set<std::string> value_fields;
        std::unordered_map<int32_t, std::pair<int32_t, uint64_t>> descriptors;
        bool thread_ping = argc == 2 && std::string(argv[1]) == "--thread-ping";
        bool invoke_proof = argc == 2 && std::string(argv[1]) == "--invoke-proof";
        bool observe_proof = argc == 2 && std::string(argv[1]) == "--observe-proof";
        bool console_construction = argc == 2 && std::string(argv[1]) == "--console-construct-proof";
        bool runtime_session = argc == 2 && std::string(argv[1]) == "--session";
        bool catalog = argc == 2 && std::string(argv[1]) == "--catalog";
        const bool matching_catalog = argc == 4 && std::string(argv[1]) == "--catalog-match";
        // Read-only exact export observation also supports generated cells whose
        // World export differs from the package basename. This does not change
        // the retained loader's canonical-path authority or invoke the engine.
        const bool resolve_export_names = argc == 4 && std::string(argv[1]) == "--resolve-export-names";
        const bool resolve_asset_names = resolve_export_names || (argc == 4 && std::string(argv[1]) == "--resolve-asset-names");
        std::string asset_package,asset_name;
        const bool catalog_values = argc == 4 && std::string(argv[1]) == "--catalog-values";
        const bool selected_catalog = catalog_values || matching_catalog || (argc == 4 && std::string(argv[1]) == "--catalog-select");
        std::unordered_set<std::string> match_names, match_classes;
        if (selected_catalog) catalog = true;
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
        else if (resolve_asset_names) {
            descriptor_pid=std::stoul(argv[2]);
            const std::string path=argv[3]; const auto dot=path.find('.');
            require(dot!=std::string::npos && path.find('.',dot+1)==std::string::npos && path.size()<1024,
                    "ASSET_PATH_INVALID");
            asset_package=path.substr(0,dot); asset_name=path.substr(dot+1);
            auto fold_asset=[](std::string value){for(char& ch:value)if(ch>='A'&&ch<='Z')ch=char(ch-'A'+'a');return value;};
            require(asset_package.rfind("/Game/",0)==0 && asset_package.size()>6 &&
                    asset_package.back()!='/' && asset_package.find("//")==std::string::npos && !asset_name.empty() &&
                    (resolve_export_names || fold_asset(asset_package.substr(asset_package.rfind('/')+1))==fold_asset(asset_name) || fold_asset(asset_package.substr(asset_package.rfind('/')+1)+"_C")==fold_asset(asset_name)),"ASSET_PATH_INVALID");
            for(char ch:asset_name) require((ch>='a'&&ch<='z') || (ch>='A'&&ch<='Z') ||
                (ch>='0'&&ch<='9') || ch=='_',"ASSET_PATH_INVALID");
            for(char ch:asset_package) require((ch>='a'&&ch<='z') || (ch>='A'&&ch<='Z') ||
                (ch>='0'&&ch<='9') || ch=='_' || ch=='/',"ASSET_PATH_INVALID");
        }
        else if (matching_catalog) {
            descriptor_pid = std::stoul(argv[2]);
            std::istringstream tokens(argv[3]); std::string token;
            while (std::getline(tokens, token, ',')) {
                require(token.size() > 2 && token.size() <= 1026 && token[1] == '=' &&
                    (token[0] == 'n' || token[0] == 'c') &&
                    match_names.size() + match_classes.size() < 256, "MATCH_SELECTOR_INVALID");
                auto& nameset = token[0] == 'n' ? match_names : match_classes;
                require(nameset.insert(token.substr(2)).second, "MATCH_SELECTOR_DUPLICATE");
            }
            require(!match_names.empty() || !match_classes.empty(), "MATCH_SELECTORS_EMPTY");
        }
        else if (argc == 4 && (selected_catalog || std::string(argv[1]) == "--describe" || std::string(argv[1]) == "--describe-script" || std::string(argv[1]) == "--read-values" || std::string(argv[1]) == "--read-table" || std::string(argv[1]) == "--describe-enums")) {
            read_script = std::string(argv[1]) == "--describe-script";
            read_table = std::string(argv[1]) == "--read-table";
            read_values = catalog_values || read_table || std::string(argv[1]) == "--read-values";
            read_enums = std::string(argv[1]) == "--describe-enums";
            descriptor_pid = std::stoul(argv[2]);
            std::string selectors=argv[3];
            const auto projection=selectors.find(';');
            if(projection!=std::string::npos) {
                require(read_values,"VALUE_PROJECTION_REQUIRES_READ");
                std::istringstream fields(selectors.substr(projection+1));std::string name;
                while(std::getline(fields,name,'|')) {
                    require(!name.empty() && name.size()<=256 && value_fields.size()<64 && value_fields.insert(name).second,"VALUE_PROJECTION_INVALID");
                }
                require(!value_fields.empty(),"VALUE_PROJECTION_EMPTY");
                selectors.resize(projection);
            }
            std::istringstream tokens(selectors); std::string token;
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
        std::unordered_set<int32_t> value_targets;
        if(catalog_values) for(const auto& selected:descriptors)value_targets.insert(selected.first);
        const bool reflection = catalog_values || !reflect_class.empty() || !bool_object.empty() || !function_name.empty() || (!descriptors.empty() && !selected_catalog);
        DWORD pid = discover_process();
        if (runtime_session) {
            wchar_t expected_pid[16]{};
            DWORD length = GetEnvironmentVariableW(L"E33_EXPECTED_GAME_PID", expected_pid, 16);
            if (length) {
                require(length < 16 && std::wstring(expected_pid) == std::to_wstring(pid),
                        "SESSION_EXPECTED_PROCESS_CHANGED");
            }
        }
        require((descriptors.empty() && !matching_catalog && !resolve_asset_names) || pid == descriptor_pid, "DESCRIPTOR_PROCESS_CHANGED");
        Handle process(OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid));
        require(process.value != nullptr, "OPEN_PROCESS_FAILED win32=" + std::to_string(GetLastError()));
        Handle snapshot(CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid));
        require(snapshot.value != INVALID_HANDLE_VALUE, "MODULE_SNAPSHOT_FAILED");
        MODULEENTRY32W module{}; module.dwSize = sizeof(module);
        require(Module32FirstW(snapshot.value, &module) != FALSE, "MODULE_NOT_FOUND");
        require(_wcsicmp(module.szModule, L"SandFall-Win64-Shipping.exe") == 0, "UNEXPECTED_MAIN_MODULE");
        const std::string fingerprint = "218a2478aad5b3a1674b5d7097ec1ac4f994abb95466f9da1407fcd39d639618";
        auto anchors = observed_image_anchors(pid, module);
        const auto& registry = anchors.first;
        const auto& names = anchors.second;
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
        if(resolve_asset_names) {
            // Verified allocator walk 1411a5a70; append-only snapshot, bounded
            // reads outside the game thread. Native invocation rechecks entries.
            const auto current=reader.get<uint32_t>(pool+8), cursor=reader.get<uint32_t>(pool+12);
            require(current<8192 && cursor<=0x20000,"ASSET_NAME_POOL_BOUNDS");
            uint32_t package_id=0,asset_id=0;
            for(uint32_t b=0;b<=current && (!package_id || !asset_id);++b) {
                const auto pointer=reader.get<uint64_t>(pool+16+uint64_t(b)*8);
                const auto extent=b==current ? cursor : 0x20000U;
                std::vector<uint8_t> bytes(extent); reader.read(pointer,bytes.data(),bytes.size());
                for(uint32_t at=0;at+2<=extent;) {
                    uint16_t h; std::memcpy(&h,bytes.data()+at,2);
                    const uint32_t length=h>>6,width=(h&1)+1;
                    if(!length) break;
                    require(at+2+length*width<=extent,"ASSET_NAME_ENTRY_BOUNDS");
                    if(width==1) {
                        const std::string value(reinterpret_cast<char*>(bytes.data()+at+2),length);
                        if(value==asset_package) package_id=(b<<16)|(at/2);
                        if(value==asset_name) asset_id=(b<<16)|(at/2);
                    }
                    at+=(length*width+3)&~1U;
                }
            }
            require(package_id && asset_id,"ASSET_NAMES_NOT_LOADED");
            require(read_name(reader,pool,package_id)==asset_package && read_name(reader,pool,asset_id)==asset_name,
                    "ASSET_NAMES_CHANGED");
            std::cout << "{\"event\":\"asset_names\",\"package\":" << quote(asset_package)
                      << ",\"asset\":" << quote(asset_name) << ",\"package_id\":" << package_id
                      << ",\"asset_id\":" << asset_id << "}\n{\"event\":\"snapshot_end\",\"emitted\":1}\n";
            return 0;
        }
        uint32_t emitted = 0, null_slots = 0, changing_slots = 0;
        // Selected catalogs are complete dependency closures, not fabricated
        // additions to an older capture. Every queued slot is checked again
        // when emitted. Scope and lifetime remain those of an observation.
        if (matching_catalog) {
            // Candidate discovery only. Every selected identity and dependency
            // is re-read by the existing strict closure emitter below.
            std::unordered_map<uint64_t, bool> type_matches;
            std::unordered_map<uint32_t,std::string> candidate_names;
            // Candidate enumeration only: copy allocator blocks once per query,
            // rather than issuing three remote reads for every distinct name.
            // Names appended after this copy use the original direct reader.
            // No copied block survives this request. The closure emitter below
            // independently re-reads selected identities and their actual names.
            const auto name_block=reader.get<uint32_t>(pool+8),name_cursor=reader.get<uint32_t>(pool+12);
            require(name_block<8192 && name_cursor<=0x20000,"MATCH_NAME_POOL_BOUNDS");
            std::unordered_map<uint32_t,std::vector<uint8_t>> name_blocks;
            auto copied_name = [&](uint32_t id) {
                const auto block=id>>16,offset=(id&0xffff)*2;
                if(block>name_block)return read_name(reader,pool,id);
                // Keep temporary memory bounded even for unusually large pools.
                if(name_blocks.size()>=512 && !name_blocks.count(block)) return read_name(reader,pool,id);
                auto known=name_blocks.find(block);
                if(known==name_blocks.end()) {
                    const auto pointer=reader.get<uint64_t>(pool+16+uint64_t(block)*8);
                    std::vector<uint8_t> bytes(block==name_block ? name_cursor : 0x20000);
                    if(!bytes.empty()) reader.read(pointer,bytes.data(),bytes.size());
                    require(reader.get<uint64_t>(pool+16+uint64_t(block)*8)==pointer,"MATCH_NAME_BLOCK_CHANGED");
                    known=name_blocks.emplace(block,std::move(bytes)).first;
                }
                const auto& bytes=known->second;
                if(offset+2>bytes.size())return read_name(reader,pool,id);
                uint16_t entry;std::memcpy(&entry,bytes.data()+offset,2);
                const uint32_t length=entry>>6,width=(entry&1) ? 2 : 1;
                if(!length || length>1023 || offset+2+length*width>bytes.size())return read_name(reader,pool,id);
                if(width==2) return read_name(reader,pool,id);
                std::string value(reinterpret_cast<const char*>(bytes.data()+offset+2),length);
                for(unsigned char c:value) require(c>=32 && c<127,"NON_ASCII_NARROW_NAME");
                return value;
            };
            auto candidate_name = [&](const ObjectHeader& header) {
                auto found=candidate_names.find(header.name_id);
                if(found==candidate_names.end()) found=candidate_names.emplace(header.name_id,copied_name(header.name_id)).first;
                return header.name_number ? found->second+"_"+std::to_string(header.name_number-1) : found->second;
            };
            std::unordered_set<uint64_t> visiting;
            std::function<bool(uint64_t)> matches_type = [&](uint64_t at) {
                if (!at || match_classes.empty()) return false;
                auto cached = type_matches.find(at);
                if (cached != type_matches.end()) return cached->second;
                require(visiting.size() < 128 && visiting.insert(at).second, "MATCH_TYPE_CYCLE");
                const auto header = reader.get<ObjectHeader>(at);
                const auto slot = item_at(header.index);
                require(slot.object == at, "MATCH_TYPE_NOT_REGISTERED");
                const auto parent = reader.get<uint64_t>(at + 0x40);
                const bool found = match_classes.count(candidate_name(header)) || matches_type(parent);
                const auto again = reader.get<ObjectHeader>(at);
                const auto slot_again = item_at(header.index);
                require(slot_again.object == at && slot_again.serial == slot.serial &&
                    std::memcmp(&header, &again, sizeof(header)) == 0 &&
                    reader.get<uint64_t>(at + 0x40) == parent, "MATCH_TYPE_CHANGED");
                visiting.erase(at);
                type_matches.emplace(at, found);
                return found;
            };
            std::vector<ObjectItem> candidate_items(65536);
            for (int32_t i = 0; i < array.num_elements; ++i) {
                if(!(i&65535)) {
                    const auto count=(array.num_elements-i)<65536 ? array.num_elements-i : 65536;
                    reader.read(chunks[uint32_t(i)>>16],candidate_items.data(),size_t(count)*sizeof(ObjectItem));
                }
                const auto item = candidate_items[i&65535];
                if (!item.object) continue;
                const auto header = reader.get<ObjectHeader>(item.object);
                if (header.index != i || !header.cls) continue;
                if (!matches_type(header.cls) && (match_names.empty() || !match_names.count(candidate_name(header)))) continue;
                require(descriptors.size() < 1024, "MATCH_RESULT_LIMIT");
                descriptors.emplace(i, std::make_pair(item.serial, item.object));
            }
            require(!descriptors.empty(), "MATCH_RESULTS_EMPTY");
        }
        std::vector<int32_t> selected_work;
        if (selected_catalog) for (const auto& entry : descriptors) selected_work.push_back(entry.first);
        auto select_dependency = [&](uint64_t address) {
            if (!selected_catalog || !address) return;
            const auto header = reader.get<ObjectHeader>(address);
            const auto item = item_at(header.index);
            require(item.object == address, "SELECTED_DEPENDENCY_NOT_REGISTERED");
            const auto identity = std::make_pair(item.serial, address);
            auto known = descriptors.find(header.index);
            if (known != descriptors.end()) {
                require(known->second == identity, "SELECTED_DEPENDENCY_CHANGED");
                return;
            }
            require(descriptors.size() < 16384, "SELECTED_DEPENDENCY_LIMIT");
            descriptors.emplace(header.index, identity);
            selected_work.push_back(header.index);
        };
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
            select_dependency(at);
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
        size_t selected_cursor = 0;
        for (int32_t next_index = 0; !limit || emitted < limit;) {
            int32_t i;
            if (selected_catalog) {
                if (selected_cursor == selected_work.size()) break;
                i = selected_work[selected_cursor++];
            } else {
                if (next_index == array.num_elements) break;
                i = next_index++;
            }
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
            if (runtime_session && !session_specimen_candidate(
                    read_name(reader, pool, object.name_id, object.name_number))) continue;
            auto cls = reader.get<ObjectHeader>(object.cls);
            require(item_at(cls.index).object == object.cls, "CLASS_NOT_REGISTERED");
            auto meta = reader.get<ObjectHeader>(cls.cls);
            require(item_at(meta.index).object == cls.cls, "METACLASS_NOT_REGISTERED");
            auto name = read_name(reader, pool, object.name_id, object.name_number);
            auto class_name = read_name(reader, pool, cls.name_id, cls.name_number);
            auto meta_name = read_name(reader, pool, meta.name_id, meta.name_number);
            bool descriptor_function = false;
            if (!descriptors.empty() && !read_values && !read_enums && !selected_catalog) {
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
                select_dependency(object.cls);
                select_dependency(cls.cls);
                select_dependency(object.outer);
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
            if (reflection && (!catalog_values || value_targets.count(i))) {
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
            if (read_enums) {
                // Builder 1413ad330 creates FName/int64 pairs; UEnum setter
                // 1412f26d0 copies them to +40, count +48/capacity +4c.
                // UUserDefinedEnum inherits UEnum's member array. This is a
                // read-only base-layout observation, with the same bounded
                // array and before/after identity checks for every subclass.
                require(derives_from_core_type(object.cls, "Enum") &&
                        object.vtable >= base && object.vtable < base + 166776832,
                        "ENUM_TARGET_TYPE_UNSUPPORTED");
                struct Members { uint64_t data; int32_t count, capacity; };
                struct Member { uint32_t name, number; int64_t value; };
                static_assert(sizeof(Members) == 16 && sizeof(Member) == 16);
                auto members = reader.get<Members>(item.object + 0x40);
                require(members.count >= 0 && members.count <= members.capacity &&
                        members.capacity <= 65536 && (!members.count || members.data),
                        "ENUM_MEMBER_BOUNDS_INVALID");
                std::vector<Member> values(members.count), verify(members.count);
                if (members.count) reader.read(members.data, values.data(), values.size()*sizeof(Member));
                std::vector<std::string> member_names;
                std::unordered_set<std::string> unique_names;
                for (const auto& value : values) {
                    auto member_name = read_name(reader, pool, value.name, value.number);
                    require(unique_names.insert(member_name).second, "ENUM_MEMBER_NAME_DUPLICATE");
                    member_names.push_back(member_name);
                }
                if (members.count) reader.read(members.data, verify.data(), verify.size()*sizeof(Member));
                auto final_members = reader.get<Members>(item.object + 0x40);
                auto final_item = item_at(i);
                auto final_header = reader.get<ObjectHeader>(item.object);
                require(std::memcmp(&members, &final_members, sizeof(members)) == 0 &&
                        (values.empty() || std::memcmp(values.data(), verify.data(), values.size()*sizeof(Member)) == 0) &&
                        final_item.object == item.object && final_item.serial == item.serial &&
                        std::memcmp(&object, &final_header, sizeof(object)) == 0,
                        "ENUM_CHANGED_DURING_READ");
                std::cout << "{\"event\":\"enum_metadata\",\"index\":" << i << ",\"members\":[";
                for (size_t member = 0; member < values.size(); ++member) {
                    if (member) std::cout << ',';
                    std::cout << "{\"name\":" << quote(member_names[member])
                              << ",\"value\":" << values[member].value << '}';
                }
                std::cout << "]}\n";
                continue;
            }
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
                if(read_script) {
                    require(!(flags&0x400),"SCRIPT_REQUIRES_BLUEPRINT_FUNCTION");
                    struct ScriptHeader { uint64_t data; int32_t count,capacity; };
                    const auto script=reader.get<ScriptHeader>(item.object+0x60);
                    require(script.data && script.count>0 && script.count<=script.capacity && script.capacity<=65536,
                            "SCRIPT_BOUNDS_UNVERIFIED");
                    std::vector<uint8_t> bytes(script.count),script_again(script.count);
                    reader.read(script.data,bytes.data(),bytes.size());
                    reader.read(script.data,script_again.data(),script_again.size());
                    const auto after=reader.get<ScriptHeader>(item.object+0x60);
                    const auto slot=item_at(i);
                    require(bytes==script_again && !std::memcmp(&script,&after,sizeof(script)) &&
                            slot.object==item.object && slot.serial==item.serial,"SCRIPT_OBSERVATION_CHANGED");
                    std::ostringstream encoded;
                    for(auto byte:bytes) encoded<<std::hex<<std::setw(2)<<std::setfill('0')<<unsigned(byte);
                    std::cout<<"{\"event\":\"blueprint_script\",\"index\":"<<i<<",\"serial\":"<<item.serial
                             <<",\"size\":"<<bytes.size()<<",\"hex\":"<<quote(encoded.str())<<"}\n";
                    // Read-only VM handler evidence. The dispatch-table address
                    // is corroborated by shipping 1413938a0; no caller address.
                    std::cout<<"{\"event\":\"script_handlers\",\"handlers\":[";
                    bool first_handler=true;
                    for(uint32_t opcode:{0x00U,0x07U,0x19U,0x1bU,0x1cU,0x20U,0x45U,0x46U,0x5fU,0x61U,0x68U,0x69U}) {
                        const auto handler=reader.get<uint64_t>(base+0x9360600+opcode*8);
                        require(handler>=base && handler<base+module.modBaseSize,"SCRIPT_HANDLER_OUTSIDE_MODULE");
                        if(!first_handler) std::cout<<',';
                        first_handler=false;
                        std::cout<<"{\"opcode\":"<<opcode<<",\"rva\":"<<quote(hex(handler-base))<<'}';
                    }
                    std::cout<<"]}\n";
                    // Candidate locations only, not a linear disassembly. The
                    // 1b handler consumes a 12-byte script name (14139b2c0).
                    // This reader never follows a script-provided memory pointer.
                    std::cout<<"{\"event\":\"script_name_candidates\",\"items\":[";
                    bool first_name=true;
                    unsigned names_seen=0;
                    for(size_t at=0;at+13<=bytes.size() && names_seen<256;++at) {
                        // EX_NameConst uses the same 12-byte script-name
                        // representation. Preserve these as candidate leads as
                        // well, so read-only audits can identify CVar names.
                        if(bytes[at]!=0x1b && bytes[at]!=0x45 && bytes[at]!=0x21) continue;
                        uint32_t id=0,number=0;
                        std::memcpy(&id,bytes.data()+at+1,4); std::memcpy(&number,bytes.data()+at+9,4);
                        if(number>65535 || (id>>16)>reader.get<uint32_t>(pool+8)) continue;
                        try {
                            const auto candidate_name=read_name(reader,pool,id,number);
                            if(candidate_name.empty() || candidate_name.size()>256) continue;
                            if(!first_name) std::cout<<',';
                            first_name=false; ++names_seen;
                            std::cout<<"{\"offset\":"<<at<<",\"opcode\":"<<unsigned(bytes[at])<<",\"name\":"<<quote(candidate_name)<<'}';
                        } catch(const std::exception&) { /* non-boundary lead */ }
                    }
                    std::cout<<"]}\n";
                }
            }
            if (reflection && (!catalog_values || value_targets.count(i))) {
                // DataTable rows use the same reflected value decoder as objects.
                // Only the verified native row-map accessor supplies row addresses.
                struct TableRow { std::string name; uint64_t address; };
                std::vector<TableRow> table_rows;
                uint64_t row_struct=0;
                std::vector<uint8_t> table_observation;
                auto table_snapshot = [&]() {
                    std::vector<uint8_t> snapshot;
                    auto append = [&](uint64_t at,size_t n) {
                        const auto old=snapshot.size();snapshot.resize(old+n);
                        reader.read(at,snapshot.data()+old,n);
                    };
                    append(item.object+40,88);
                    const auto map=item.object+48;
                    const auto data=reader.get<uint64_t>(map),heap=reader.get<uint64_t>(map+32);
                    const auto count=reader.get<int32_t>(map+8),cap=reader.get<int32_t>(map+12),
                        bits=reader.get<int32_t>(map+40),bitcap=reader.get<int32_t>(map+44),free=reader.get<int32_t>(map+52);
                    require(count>=0 && count<=cap && cap<=4096 && count<=4096 && bits==count && bitcap>=bits && bitcap<=4096 &&
                        free>=0 && free<=count && (heap || bitcap<=128) && (!count || (data && !(data&7))),"TABLE_MAP_BOUNDS");
                    const auto masks=heap?heap:map+16;
                    if(count) {append(data,size_t(count)*24);append(masks,size_t((count+31)/32)*4);}
                    int live=0;std::unordered_set<std::string> names;
                    for(int n=0;n<count;++n) {
                        if(!(reader.get<uint32_t>(masks+uint64_t(n/32)*4)&(uint32_t(1)<<(n%32))))continue;
                        ++live;const auto at=data+uint64_t(n)*24,key=reader.get<uint64_t>(at),row=reader.get<uint64_t>(at+8);
                        const auto row_name=read_name(reader,pool,uint32_t(key),uint32_t(key>>32));
                        require(row && !(row&7) && names.insert(row_name).second,"TABLE_ROW_INVALID");
                        if(table_observation.empty())table_rows.push_back({row_name,row});
                        const auto extent=reader.get<int32_t>(row_struct+0x58);
                        require(extent>0 && extent<=4096,"TABLE_ROW_EXTENT");append(row,size_t(extent));
                    }
                    require(live==count-free,"TABLE_OCCUPANCY_CHANGED");return snapshot;
                };
                if(read_table) {
                    require(class_name=="DataTable" || class_name=="CompositeDataTable","TABLE_TYPE_UNSUPPORTED");
                    const auto cls_outer=reader.get<ObjectHeader>(cls.outer);
                    require(read_name(reader,pool,cls_outer.name_id,cls_outer.name_number)=="/Script/Engine","TABLE_CLASS_OWNER");
                    const uint8_t expected[]={0x48,0x8d,0x41,0x30,0xc3};uint8_t actual[5];
                    reader.read(reader.get<uint64_t>(reader.get<uint64_t>(item.object)+0x2d8),actual,5);
                    require(!std::memcmp(actual,expected,5),"TABLE_ACCESSOR_UNSUPPORTED");
                    row_struct=reader.get<uint64_t>(item.object+40);
                    const auto rh=reader.get<ObjectHeader>(row_struct),rc=reader.get<ObjectHeader>(rh.cls);
                    require(item_at(rh.index).object==row_struct && item_at(rc.index).object==rh.cls &&
                        (read_name(reader,pool,rc.name_id,rc.name_number)=="ScriptStruct" ||
                         read_name(reader,pool,rc.name_id,rc.name_number)=="UserDefinedStruct"),"TABLE_ROW_TYPE_UNSUPPORTED");
                    table_observation=table_snapshot();
                } else table_rows.push_back({"",item.object});
                for(const auto& table_row:table_rows) {
                if(read_table)std::cout<<"{\"event\":\"table_row\",\"name\":"<<quote(table_row.name)<<"}\n";
                const auto value_base=table_row.address;
                // Derived from target routines 1412792f0, 1412813d0, 14134c3b0,
                // 1412ab240 and 1412aca00. Research metadata, not callable handles.
                uint64_t owner = read_table ? row_struct : bool_object.empty() && !read_values ? item.object : object.cls;
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
                        if(read_values && !value_fields.empty() && !value_fields.count(field_name)) { field=p.next; continue; }
                        auto type = read_name(reader, pool, uint32_t(type_name), uint32_t(type_name >> 32));
                        auto p_again = reader.get<PropertyPrefix>(field);
                        require(std::memcmp(&p, &p_again, sizeof(p)) == 0, "PROPERTY_CHANGED");
                        std::cout << "{\"event\":\"property_metadata\",\"owner\":" << quote(owner_name)
                                  << ",\"owner_index\":" << header.index
                                  << ",\"field_address\":" << quote(hex(field))
                                  << ",\"name_id\":" << p.name_id << ",\"name_number\":" << p.number
                                  << ",\"name_base\":" << quote(read_name(reader, pool, p.name_id))
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
                        if (type == "MapProperty") {
                            // FMapProperty export 14136a7f0 uses Key/Value +70/+78,
                            // value offset +80, pair stride +8c, allocator flag +98.
                            for (unsigned part = 0; part < 2; ++part) {
                                const auto child_address = reader.get<uint64_t>(field + 0x70 + part * 8);
                                require(child_address && child_address != field, "MAP_CHILD_INVALID");
                                const auto child = reader.get<PropertyPrefix>(child_address);
                                require(child.owner == field && child.dimension == 1 &&
                                        child.element_size > 0 && child.element_size <= 65536 &&
                                        (reader.get<uint64_t>(child.type + 0x10) & 0x8000), "MAP_CHILD_LAYOUT");
                                const auto id = reader.get<uint64_t>(child.type);
                                const auto map_child_name = read_name(reader, pool, uint32_t(id), uint32_t(id >> 32));
                                const std::string prefix = part ? "map_value" : "map_key";
                                std::cout << ',' << quote(prefix + "_type") << ':' << quote(map_child_name)
                                          << ',' << quote(prefix + "_size") << ':' << child.element_size
                                          << ',' << quote(prefix + "_offset") << ':' << child.offset;
                                if(map_child_name=="StructProperty") {
                                    const auto reference=reader.get<uint64_t>(child_address+0x70);
                                    const auto structure=reader.get<ObjectHeader>(reference);
                                    const auto slot=item_at(structure.index);
                                    require(slot.object==reference && derives_from_core_type(structure.cls,"ScriptStruct"),
                                            "MAP_STRUCT_TYPE_INVALID");
                                    const auto structure_again=reader.get<ObjectHeader>(reference);
                                    const auto slot_again=item_at(structure.index);
                                    require(!std::memcmp(&structure,&structure_again,sizeof(structure)) &&
                                            slot_again.object==reference && slot_again.serial==slot.serial &&
                                            reader.get<uint64_t>(child_address+0x70)==reference,"MAP_STRUCT_TYPE_CHANGED");
                                    std::cout << ',' << quote(prefix+"_struct_index") << ':' << structure.index
                                              << ',' << quote(prefix+"_struct_serial") << ':' << slot.serial
                                              << ',' << quote(prefix+"_struct_address") << ':' << quote(hex(reference))
                                              << ',' << quote(prefix+"_struct_name") << ':'
                                              << quote(read_name(reader,pool,structure.name_id,structure.name_number));
                                }
                                const auto map_child_again = reader.get<PropertyPrefix>(child_address);
                                require(std::memcmp(&child, &map_child_again, sizeof(child)) == 0 &&
                                        reader.get<uint64_t>(field + 0x70 + part * 8) == child_address,
                                        "MAP_CHILD_CHANGED");
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
                            // The same verified FProperty subclasses occur under
                            // ArrayProperty.Inner. Preserve their referenced type
                            // identities; element size alone does not identify FKey.
                            const bool inner_struct = child_name == "StructProperty";
                            const bool inner_enum = child_name == "EnumProperty" || child_name == "ByteProperty";
                            const bool inner_class = child_name == "ClassProperty" || child_name == "SoftClassProperty";
                            const bool inner_object = child_name == "ObjectProperty" || child_name == "WeakObjectProperty";
                            if (inner_struct || inner_enum || inner_class || inner_object) {
                                const auto ref_offset = inner_class || child_name == "EnumProperty" ? 0x78 : 0x70;
                                const auto reference = reader.get<uint64_t>(inner + ref_offset);
                                require(reference || child_name == "ByteProperty", "INNER_TYPE_REFERENCE_NULL");
                                if (reference) {
                                    const auto target = reader.get<ObjectHeader>(reference);
                                    const auto target_item = item_at(target.index);
                                    require(target_item.object == reference, "INNER_TYPE_NOT_REGISTERED");
                                    require(derives_from_core_type(target.cls, inner_struct ? "ScriptStruct" :
                                            inner_enum ? "Enum" : "Class"), "INNER_TYPE_CLASS_MISMATCH");
                                    const auto target_name = read_name(reader, pool, target.name_id, target.name_number);
                                    const auto target_again = reader.get<ObjectHeader>(reference);
                                    const auto item_again = item_at(target.index);
                                    const auto final_child = reader.get<PropertyPrefix>(inner);
                                    require(std::memcmp(&target, &target_again, sizeof(target)) == 0 &&
                                            item_again.object == reference && item_again.serial == target_item.serial &&
                                            std::memcmp(&child, &final_child, sizeof(child)) == 0 &&
                                            reader.get<uint64_t>(inner + ref_offset) == reference &&
                                            reader.get<uint64_t>(field + inner_offset) == inner,
                                            "INNER_TYPE_CHANGED");
                                    const std::string prefix = inner_struct ? "inner_struct" : inner_enum ? "inner_enum" :
                                                               inner_class ? "inner_meta_class" : "inner_property_class";
                                    std::cout << "," << quote(prefix + "_name") << ":" << quote(target_name)
                                              << "," << quote(prefix + "_index") << ":" << target.index
                                              << "," << quote(prefix + "_serial") << ":" << target_item.serial
                                              << "," << quote(prefix + "_address") << ":" << quote(hex(reference));
                                }
                            }
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
                                require(value_type == "ObjectProperty" || value_type == "ClassProperty", "SCALAR_TYPE_UNSUPPORTED");
                                if (!raw) value << "null";
                                else {
                                    const auto target = reader.get<ObjectHeader>(raw);
                                    const auto slot = item_at(target.index);
                                    require(slot.object == raw, "VALUE_REFERENCE_NOT_REGISTERED");
                                    if(value_type == "ClassProperty")
                                        require(derives_from_core_type(target.cls,"Class"),"VALUE_CLASS_REFERENCE_INVALID");
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
                                value_type == "NameProperty" || value_type == "ObjectProperty" || value_type == "ClassProperty" || value_type == "DoubleProperty" ? 8 : 0;
                        };
                        // Copied reflected fields only: never reconstruct or own
                        // non-reflected state (for example FKey's shared pointer).
                        size_t struct_budget = 4096;
                        size_t struct_string_budget = 262144;
                        std::function<std::string(uint64_t, const PropertyPrefix&, uint64_t,
                            const uint8_t*, unsigned)> struct_json;
                        std::function<std::string(uint64_t, const PropertyPrefix&, uint64_t,
                            unsigned)> map_json;
                        struct_json = [&](uint64_t property, const PropertyPrefix& layout, uint64_t at,
                                          const uint8_t* bytes, unsigned depth) -> std::string {
                            require(depth < 4 && struct_budget > 0, "STRUCT_DEPTH_OR_NODE_LIMIT");
                            --struct_budget;
                            require(layout.element_size > 0 && layout.element_size <= 65536, "STRUCT_VALUE_SIZE_LIMIT");
                            const auto ref = reader.get<uint64_t>(property + 0x70);
                            const auto structure = reader.get<ObjectHeader>(ref);
                            const auto slot = item_at(structure.index);
                            require(slot.object == ref && derives_from_core_type(structure.cls, "ScriptStruct"),
                                    "STRUCT_VALUE_TYPE_INVALID");
                            const auto struct_name = read_name(reader, pool, structure.name_id, structure.name_number);
                            // User-defined S_InteractiveMusicParameters has 17
                            // reflected bytes in a 24-byte property slot. Read
                            // fields only inside the descriptor extent; trailing
                            // storage padding is never interpreted or exposed.
                            // This is observation-only, not a by-value call ABI.
                            const auto reflected_extent=reader.get<int32_t>(ref + 0x58);
                            require(reflected_extent>=0 && reflected_extent<=layout.element_size,
                                    "STRUCT_VALUE_EXTENT_MISMATCH");
                            std::ostringstream members;
                            std::unordered_set<uint64_t> struct_owners, struct_fields;
                            std::unordered_set<std::string> names;
                            bool truncated = false;
                            size_t count = 0;
                            for (auto current = ref; current;) {
                                require(struct_owners.size() < 64 && struct_owners.insert(current).second, "STRUCT_OWNER_CYCLE");
                                const auto current_header = reader.get<ObjectHeader>(current);
                                const auto current_slot = item_at(current_header.index);
                                require(current_slot.object == current && derives_from_core_type(current_header.cls, "ScriptStruct"),
                                        "STRUCT_OWNER_INVALID");
                                const auto first_member = reader.get<uint64_t>(current + 0x50);
                                const auto super_struct = reader.get<uint64_t>(current + 0x40);
                                const auto extent = reader.get<int32_t>(current + 0x58);
                                require(extent >= 0 && extent <= layout.element_size, "STRUCT_OWNER_EXTENT_INVALID");
                                for (auto member = first_member; member;) {
                                    if (count == 64) { truncated = true; break; }
                                    require(struct_fields.size() < 4096 && struct_fields.insert(member).second, "STRUCT_FIELD_CYCLE_OR_LIMIT");
                                    const auto child = reader.get<PropertyPrefix>(member);
                                    require(child.owner == (current | 1ULL) && child.offset >= 0 && child.dimension > 0 &&
                                            child.element_size > 0 && int64_t(child.offset) + int64_t(child.dimension) * child.element_size <= extent &&
                                            (reader.get<uint64_t>(child.type + 0x10) & 0x8000), "STRUCT_FIELD_LAYOUT_INVALID");
                                    const auto id = reader.get<uint64_t>(child.type);
                                    const auto kind = read_name(reader, pool, uint32_t(id), uint32_t(id >> 32));
                                    const auto member_name = read_name(reader, pool, child.name_id, child.number);
                                    if (names.insert(member_name).second) {
                                        if (count++) members << ',';
                                        members << "{\"name\":" << quote(member_name) << ",\"type\":" << quote(kind);
                                        try {
                                            require(struct_budget > 0, "STRUCT_NODE_LIMIT"); --struct_budget;
                                            require(child.dimension == 1, "STRUCT_STATIC_ARRAY_UNSUPPORTED");
                                            const auto source = bytes + child.offset;
                                            std::string encoded;
                                            if (kind == "StructProperty") {
                                                encoded = struct_json(member, child, at + child.offset, source, depth + 1);
                                            } else if (kind == "MapProperty") {
                                                // Nested maps currently admit only the objective-status schema.
                                                // Publish its independently observed element types for Python validation.
                                                const auto key = reader.get<uint64_t>(member + 0x70);
                                                const auto val = reader.get<uint64_t>(member + 0x78);
                                                const auto key_layout = reader.get<PropertyPrefix>(key);
                                                const auto val_layout = reader.get<PropertyPrefix>(val);
                                                const auto key_id = reader.get<uint64_t>(key_layout.type);
                                                const auto val_id = reader.get<uint64_t>(val_layout.type);
                                                const auto key_kind = read_name(reader, pool, uint32_t(key_id), uint32_t(key_id >> 32));
                                                const auto val_kind = read_name(reader, pool, uint32_t(val_id), uint32_t(val_id >> 32));
                                                require(key_kind == "NameProperty" && val_kind == "ByteProperty",
                                                        "STRUCT_MAP_ELEMENT_TYPE_UNSUPPORTED");
                                                encoded = map_json(member, child, at + child.offset, depth + 1);
                                                const auto key_again = reader.get<PropertyPrefix>(key);
                                                const auto val_again = reader.get<PropertyPrefix>(val);
                                                require(reader.get<uint64_t>(member + 0x70) == key &&
                                                        reader.get<uint64_t>(member + 0x78) == val &&
                                                        !std::memcmp(&key_layout, &key_again, sizeof(key_layout)) &&
                                                        !std::memcmp(&val_layout, &val_again, sizeof(val_layout)) &&
                                                        reader.get<uint64_t>(key_layout.type) == key_id &&
                                                        reader.get<uint64_t>(val_layout.type) == val_id,
                                                        "STRUCT_MAP_DESCRIPTOR_CHANGED");
                                                members << ",\"map_key_type\":" << quote(key_kind)
                                                        << ",\"map_value_type\":" << quote(val_kind);
                                            } else if (kind == "StrProperty") {
                                                // Copy FString contents, never expose or own its pointer.
                                                struct StringHeader { uint64_t data; int32_t count, capacity; };
                                                static_assert(sizeof(StringHeader) == 16);
                                                require(child.element_size == sizeof(StringHeader), "STRING_PROPERTY_LAYOUT_INVALID");
                                                StringHeader text; std::memcpy(&text, source, sizeof(text));
                                                require(text.count >= 0 && text.count <= text.capacity && text.capacity <= 1048576,
                                                        "STRING_COUNTS_INVALID");
                                                require(text.count <= 4097 && size_t(text.count) <= struct_string_budget,
                                                        "STRUCT_STRING_SIZE_LIMIT");
                                                struct_string_budget -= text.count;
                                                std::wstring wide(text.count, 0), repeated(text.count, 0);
                                                if (text.count) {
                                                    require(text.data && !(text.data & 1), "STRING_DATA_INVALID");
                                                    reader.read(text.data, wide.data(), wide.size() * 2);
                                                    reader.read(text.data, repeated.data(), repeated.size() * 2);
                                                    require(wide == repeated, "STRING_CONTENT_CHANGED");
                                                    require(wide.back() == 0, "STRING_TERMINATOR_INVALID");
                                                    wide.pop_back();
                                                }
                                                const auto text_again = reader.get<StringHeader>(at + child.offset);
                                                require(std::memcmp(&text, &text_again, sizeof(text)) == 0, "STRING_HEADER_CHANGED");
                                                std::string decoded;
                                                if (!wide.empty()) {
                                                    const auto size = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, wide.data(),
                                                        static_cast<int>(wide.size()), nullptr, 0, nullptr, nullptr);
                                                    require(size > 0, "STRING_UTF16_INVALID"); decoded.resize(size);
                                                    require(WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, wide.data(),
                                                        static_cast<int>(wide.size()), decoded.data(), size, nullptr, nullptr) == size,
                                                        "STRING_UTF16_INVALID");
                                                }
                                                encoded = quote(decoded);
                                            } else if (kind == "BoolProperty") {
                                                const auto encoding = reader.get<uint32_t>(member + 0x70);
                                                const auto offset = uint8_t(encoding >> 8), mask = uint8_t(encoding >> 24);
                                                require(mask && offset < child.element_size, "STRUCT_BOOL_ENCODING_INVALID");
                                                encoded = (source[offset] & mask) ? "true" : "false";
                                                require(reader.get<uint32_t>(member + 0x70) == encoding, "STRUCT_BOOL_ENCODING_CHANGED");
                                            } else {
                                                const auto width = scalar_width(kind);
                                                require(width && width == child.element_size, "STRUCT_MEMBER_TYPE_UNSUPPORTED");
                                                uint64_t raw = 0; std::memcpy(&raw, source, width);
                                                encoded = scalar_json(kind, raw);
                                            }
                                            members << ",\"value\":" << encoded;
                                        } catch (const std::exception& error) {
                                            members << ",\"error\":" << quote(error.what());
                                        }
                                        members << '}';
                                    }
                                    const auto child_again = reader.get<PropertyPrefix>(member);
                                    require(std::memcmp(&child, &child_again, sizeof(child)) == 0, "STRUCT_MEMBER_CHANGED");
                                    member = child.next;
                                }
                                const auto current_again = reader.get<ObjectHeader>(current);
                                const auto slot_again = item_at(current_header.index);
                                require(std::memcmp(&current_header, &current_again, sizeof(current_header)) == 0 &&
                                        slot_again.object == current && slot_again.serial == current_slot.serial &&
                                        reader.get<uint64_t>(current + 0x50) == first_member &&
                                        reader.get<uint64_t>(current + 0x40) == super_struct &&
                                        reader.get<int32_t>(current + 0x58) == extent, "STRUCT_DESCRIPTOR_CHANGED");
                                if (truncated) break;
                                current = super_struct;
                            }
                            std::vector<uint8_t> repeated(layout.element_size);
                            reader.read(at, repeated.data(), repeated.size());
                            const auto final_property = reader.get<PropertyPrefix>(property);
                            const auto final_slot = item_at(structure.index);
                            require(std::memcmp(bytes, repeated.data(), repeated.size()) == 0 &&
                                    std::memcmp(&layout, &final_property, sizeof(layout)) == 0 &&
                                    reader.get<uint64_t>(property + 0x70) == ref &&
                                    final_slot.object == ref && final_slot.serial == slot.serial, "STRUCT_OBSERVATION_CHANGED");
                            std::ostringstream out;
                            out << "{\"$struct\":{\"type\":{\"index\":" << structure.index << ",\"serial\":" << slot.serial
                                << ",\"address\":" << quote(hex(ref)) << ",\"name\":" << quote(struct_name)
                                << "},\"fields\":[" << members.str() << "],\"truncated\":" << (truncated ? "true" : "false") << "}}";
                            return out.str();
                        };
                        map_json = [&](uint64_t property, const PropertyPrefix& layout, uint64_t at,
                                       unsigned depth) -> std::string {
                            require(depth < 4 && struct_budget > 0, "MAP_DEPTH_OR_NODE_LIMIT");
                            --struct_budget;
                            // Read-only, bounded supported map pairs, including Name->Byte.
                            // Storage layout follows target export 14136a7f0;
                            // frozen/relative allocators and other types fail closed.
                            require(layout.dimension == 1 && layout.element_size == 80, "MAP_LAYOUT_UNSUPPORTED");
                            uint8_t descriptor[0x30], descriptor_again[0x30];
                            reader.read(property + 0x70, descriptor, sizeof(descriptor));
                            auto d32 = [&](size_t off) { int32_t v; std::memcpy(&v, descriptor + off, 4); return v; };
                            auto d64 = [&](size_t off) { uint64_t v; std::memcpy(&v, descriptor + off, 8); return v; };
                            require(!(descriptor[0x28] & 1), "MAP_ALLOCATOR_UNSUPPORTED");
                            const auto key_address = d64(0), value_address = d64(8);
                            require(key_address && value_address && key_address != property &&
                                    value_address != property && key_address != value_address, "MAP_INNER_INVALID");
                            const auto key_layout = reader.get<PropertyPrefix>(key_address);
                            const auto value_layout = reader.get<PropertyPrefix>(value_address);
                            auto map_type = [&](const PropertyPrefix& child) {
                                require(reader.get<uint64_t>(child.type + 0x10) & 0x8000, "MAP_INNER_TYPE_INVALID");
                                const auto id = reader.get<uint64_t>(child.type);
                                return read_name(reader, pool, uint32_t(id), uint32_t(id >> 32));
                            };
                            const auto key_kind = map_type(key_layout), value_kind = map_type(value_layout);
                            const bool name_byte = key_kind == "NameProperty" && value_kind == "ByteProperty";
                            const bool name_bool = key_kind == "NameProperty" && value_kind == "BoolProperty";
                            const bool byte_struct = key_kind == "ByteProperty" && value_kind == "StructProperty";
                            const bool name_struct = key_kind == "NameProperty" && value_kind == "StructProperty";
                            const bool name_object = key_kind == "NameProperty" && value_kind == "ObjectProperty";
                            const bool byte_double = key_kind == "ByteProperty" && value_kind == "DoubleProperty";
                            const bool byte_int = key_kind == "ByteProperty" && value_kind == "IntProperty";
                            const bool struct_object = key_kind == "StructProperty" && value_kind == "ObjectProperty";
                            const bool struct_struct = key_kind == "StructProperty" && value_kind == "StructProperty";
                            require(name_byte || name_bool || byte_struct || name_struct || name_object || byte_double || byte_int || struct_object || struct_struct,
                                    "MAP_ELEMENT_TYPE_UNSUPPORTED");
                            const bool struct_key = struct_object || struct_struct;
                            const bool struct_value = byte_struct || name_struct || struct_struct;
                            const auto value_offset = d32(0x10), stride = d32(0x1c);
                            require(key_layout.owner == property && value_layout.owner == property &&
                                    key_layout.dimension == 1 && value_layout.dimension == 1 &&
                                    key_layout.offset == 0 && (struct_key ?
                                        (key_layout.element_size > 0 && key_layout.element_size <= 128) :
                                        key_layout.element_size == ((name_byte || name_bool || name_struct || name_object) ? 8 : 1)) &&
                                    value_layout.offset == value_offset && value_layout.element_size > 0 &&
                                    ((name_bool || name_byte) ? value_layout.element_size == 1 :
                                     struct_value ? value_layout.element_size <= 512 : value_layout.element_size == (byte_int ? 4 : 8)) &&
                                    value_offset >= key_layout.element_size && value_offset < stride && stride <= 1024 &&
                                    value_layout.element_size <= stride - value_offset,
                                    "MAP_PAIR_LAYOUT_INVALID");
                            const auto key_constraint = struct_key ? reader.get<uint64_t>(key_address + 0x70) : 0;
                            const auto value_constraint = !(name_byte || byte_double || byte_int) ? reader.get<uint64_t>(value_address + 0x70) : 0;
                            require(!name_bool || uint32_t(value_constraint) == 0xff010001, "MAP_BOOL_ENCODING_UNSUPPORTED");
                            uint8_t storage[80], storage_again[80];
                            reader.read(at, storage, sizeof(storage));
                            auto s32 = [&](size_t off) { int32_t v; std::memcpy(&v, storage + off, 4); return v; };
                            auto s64 = [&](size_t off) { uint64_t v; std::memcpy(&v, storage + off, 8); return v; };
                            const auto count = s32(8), capacity = s32(12), bit_count = s32(40), bit_capacity = s32(44), free_count = s32(52);
                            require(count >= 0 && count <= capacity && capacity <= 4096 && bit_count == count &&
                                    bit_capacity >= bit_count && bit_capacity <= 4096 && free_count >= 0 && free_count <= count,
                                    "MAP_STORAGE_BOUNDS");
                            const auto data = s64(0), heap_bits = s64(32);
                            require(!count || (data && !(data & 7)), "MAP_DATA_INVALID");
                            require(heap_bits || bit_capacity <= 128, "MAP_INLINE_BITS_OVERFLOW");
                            const auto bits_at = heap_bits ? heap_bits : at + 16;
                            std::vector<uint8_t> bytes(size_t(count) * stride), repeated(bytes.size());
                            std::vector<uint32_t> bits((count + 31) / 32), bits_again(bits.size());
                            if (count) {
                                reader.read(data, bytes.data(), bytes.size());
                                reader.read(bits_at, bits.data(), bits.size() * 4);
                            }
                            std::ostringstream pairs;
                            int32_t live = 0;
                            for (int32_t index = 0; index < count; ++index) {
                                if (!(bits[index / 32] & (uint32_t(1) << (index % 32)))) continue;
                                require(struct_budget > 0, "MAP_NODE_LIMIT"); --struct_budget;
                                const auto source = bytes.data() + size_t(index) * stride;
                                if (live++) pairs << ',';
                                pairs << '[';
                                if (struct_key) {
                                    pairs << struct_json(key_address, key_layout,
                                        data + uint64_t(index) * stride, source, depth + 1);
                                } else if (key_kind == "NameProperty") {
                                    uint64_t raw; std::memcpy(&raw, source, 8);
                                    pairs << scalar_json(key_kind, raw);
                                } else {
                                    pairs << unsigned(source[0]);
                                }
                                pairs << ',';
                                if (name_bool) {
                                    require(source[value_offset] <= 1, "MAP_BOOL_VALUE_INVALID");
                                    pairs << (source[value_offset] ? "true" : "false");
                                } else if (struct_value) {
                                    pairs << struct_json(value_address, value_layout,
                                        data + uint64_t(index) * stride + value_offset, source + value_offset, depth + 1);
                                } else {
                                    uint64_t raw=0; std::memcpy(&raw, source + value_offset, name_byte ? 1 : byte_int ? 4 : 8);
                                    pairs << scalar_json(value_kind, raw);
                                }
                                pairs << ']';
                            }
                            require(live == count - free_count, "MAP_OCCUPANCY_MISMATCH");
                            if (count) {
                                reader.read(data, repeated.data(), repeated.size());
                                reader.read(bits_at, bits_again.data(), bits_again.size() * 4);
                            }
                            reader.read(at, storage_again, sizeof(storage_again));
                            reader.read(property + 0x70, descriptor_again, sizeof(descriptor_again));
                            const auto key_again = reader.get<PropertyPrefix>(key_address);
                            const auto value_again = reader.get<PropertyPrefix>(value_address);
                            const auto map_again = reader.get<PropertyPrefix>(property);
                            require(bytes == repeated && bits == bits_again &&
                                    !std::memcmp(storage, storage_again, sizeof(storage)) &&
                                    !std::memcmp(descriptor, descriptor_again, sizeof(descriptor)) &&
                                    !std::memcmp(&key_layout, &key_again, sizeof(key_layout)) &&
                                    !std::memcmp(&value_layout, &value_again, sizeof(value_layout)) &&
                                    !std::memcmp(&layout, &map_again, sizeof(layout)) &&
                                    (!struct_key || reader.get<uint64_t>(key_address + 0x70) == key_constraint) &&
                                    (name_byte || byte_double || byte_int || reader.get<uint64_t>(value_address + 0x70) == value_constraint), "MAP_OBSERVATION_CHANGED");
                            std::ostringstream out;
                            out << "{\"$map\":{\"length\":" << live << ",\"items\":[" << pairs.str() << "]}}";
                            return out.str();
                        };
                        if (read_values && type == "StructProperty") {
                            try {
                                require(p.dimension <= 64 && p.element_size <= 65536, "STRUCT_VALUE_LIMIT");
                                for (int32_t element = 0; element < p.dimension; ++element) {
                                    const auto at = value_base + p.offset + uint64_t(element) * p.element_size;
                                    std::vector<uint8_t> bytes(p.element_size);
                                    reader.read(at, bytes.data(), bytes.size());
                                    const auto value = struct_json(field, p, at, bytes.data(), 0);
                                    std::cout << "{\"event\":\"stored_value\",\"owner_index\":" << header.index
                                              << ",\"name\":" << quote(field_name) << ",\"element\":" << element
                                              << ",\"value\":" << value << "}\n";
                                }
                            } catch (const std::exception& error) {
                                std::cout << "{\"event\":\"stored_value_error\",\"owner_index\":" << header.index
                                          << ",\"name\":" << quote(field_name) << ",\"error\":" << quote(error.what()) << "}\n";
                            }
                        }
                        if (read_values && type == "MapProperty") {
                            try {
                                const auto value = map_json(field, p, value_base + p.offset, 0);
                                std::cout << "{\"event\":\"stored_value\",\"owner_index\":" << header.index
                                          << ",\"name\":" << quote(field_name) << ",\"element\":0,\"value\":" << value << "}\n";
                            } catch (const std::exception& error) {
                                std::cout << "{\"event\":\"stored_value_error\",\"owner_index\":" << header.index
                                          << ",\"name\":" << quote(field_name) << ",\"error\":" << quote(error.what()) << "}\n";
                            }
                        }
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
                                const auto width = child_type == "StructProperty" ? child.element_size : scalar_width(child_type);
                                require(width != 0, "ARRAY_ELEMENT_TYPE_UNSUPPORTED");
                                require(width > 0 && width <= 65536, "ARRAY_ELEMENT_SIZE_LIMIT");
                                require(child.owner == field && child.dimension == 1 && child.offset == 0 &&
                                        child.element_size == width && (reader.get<uint64_t>(child.type + 0x10) & 0x8000),
                                        "ARRAY_INNER_LAYOUT_INVALID");
                                for (int32_t element = 0; element < p.dimension; ++element) {
                                    const auto at = value_base + p.offset + uint64_t(element) * 16;
                                    const auto observed_array = reader.get<ArrayHeader>(at);
                                    require(observed_array.count >= 0 && observed_array.count <= observed_array.capacity && observed_array.capacity <= 1048576,
                                            "ARRAY_COUNTS_INVALID");
                                    const auto copied = std::min(observed_array.count, 256);
                                    std::vector<uint8_t> bytes(size_t(copied) * width), repeated(bytes.size());
                                    if (copied) {
                                        require(observed_array.data && (observed_array.data & 1) == 0, "ARRAY_DATA_INVALID");
                                        reader.read(observed_array.data, bytes.data(), bytes.size());
                                    }
                                    std::ostringstream values;
                                    for (int32_t index = 0; index < copied; ++index) {
                                        if (index) values << ',';
                                        const auto source = bytes.data() + size_t(index) * width;
                                        if (child_type == "StructProperty") {
                                            values << struct_json(inner, child, observed_array.data + uint64_t(index) * width, source, 0);
                                        } else {
                                            uint64_t raw = 0; std::memcpy(&raw, source, width);
                                            values << scalar_json(child_type, raw);
                                        }
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
                                        const auto at = value_base + p.offset + uint64_t(element) * width;
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
                                    const auto at = value_base + p.offset + uint64_t(element) * 16;
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
                                uint64_t at = value_base + p.offset +
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
                }
                if(read_table)require(table_snapshot()==table_observation,"TABLE_OBSERVATION_CHANGED");
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
    } catch (const TargetProcessExited& error) {
        std::cerr << "{\"event\":\"target_exited\",\"exit_code\":" << error.exit_code << "}\n";
        return error.exit_code == 0 ? 0 : 1;
    } catch (const std::exception& error) {
        std::cerr << "{\"event\":\"error\",\"message\":" << quote(error.what()) << "}\n";
        return 1;
    }
}

int main(int argc, char** argv) {
    if (argc == 3 && std::string(argv[1]) == "--reader-session")
        return run_reader_session(argv[2], run_query);
    return run_query(argc, argv);
}
