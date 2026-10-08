#pragma once
#include <cstring>

// The first actual invocation experiment is intentionally a single known getter.
// General function invocation must later add argument marshalling and lifetime rules.
template<class T> T local_read(uint64_t address) { return *reinterpret_cast<const T*>(address); }
inline bool exact_name(uint64_t base, uint64_t fname, const char* expected) {
    if (local_read<uint32_t>(fname + 4)) return false;
    uint32_t id = local_read<uint32_t>(fname);
    if ((id >> 16) >= 8192) return false;
    uint64_t entry = local_read<uint64_t>(base + 0x92aadc0 + 0x10 + uint64_t(id >> 16) * 8) + (id & 65535) * 2;
    uint16_t header = local_read<uint16_t>(entry);
    size_t length = std::strlen(expected);
    return !(header & 1) && (header >> 6) == length &&
           (id & 65535) * 2 + 2 + length <= 0x20000 &&
           std::memcmp(reinterpret_cast<void*>(entry + 2), expected, length) == 0;
}
inline uint64_t fixed_slot(uint64_t base, int32_t index, int32_t serial) {
    int32_t count = local_read<int32_t>(base + 0x9361b84);
    int32_t chunks_count = local_read<int32_t>(base + 0x9361b8c);
    if (index < 0 || index >= count || count > 100000000 || chunks_count <= (index >> 16) || chunks_count > 8192) return 0;
    uint64_t chunks = local_read<uint64_t>(base + 0x9361b70);
    uint64_t slot = local_read<uint64_t>(chunks + uint64_t(index >> 16) * 8) + uint64_t(index & 65535) * 24;
    uint64_t object = local_read<uint64_t>(slot);
    if (!object || local_read<int32_t>(slot + 0x10) != serial || local_read<int32_t>(object + 0xc) != index) return 0;
    return object;
}
inline uint32_t invoke_fixed_body(SchedulePacket* packet, uint64_t allowed_entry = 0) {
    uint64_t base = reinterpret_cast<uint64_t>(GetModuleHandleW(nullptr));
    if (!base || local_read<uint16_t>(base) != 0x5a4d) return 10;
    auto* nt = reinterpret_cast<const IMAGE_NT_HEADERS64*>(base + local_read<uint32_t>(base + 0x3c));
    if (nt->Signature != IMAGE_NT_SIGNATURE || nt->FileHeader.Machine != IMAGE_FILE_MACHINE_AMD64 ||
        nt->OptionalHeader.SizeOfImage != 166776832 || local_read<DWORD>(base + 0x9272d30) != GetCurrentThreadId()) return 11;
    const uint8_t dispatcher[] = {0x40,0x55,0x56,0x57,0x41,0x54,0x41,0x55,0x41,0x56,0x41,0x57,0x48,0x81,0xec,0x10,0x1,0,0,0x48,0x8d,0x6c,0x24,0x30,0x48,0x89,0x9d,0x38,0x1,0,0,0x48};
    const uint8_t actor_dispatcher[] = {0x48,0x89,0x5c,0x24,0x10,0x48,0x89,0x6c,0x24,0x18,0x57,0x48,0x83,0xec,0x20,0xf7,0x82,0xb0,0,0,0,0,0x4,0,0,0x49,0x8b,0xe8,0x48,0x8b,0xda,0x48};
    const uint8_t thunk[] = {0x48,0x8b,0x42,0x20,0x45,0x33,0xc9,0x48,0x85,0xc0,0x41,0xf,0x95,0xc1,0x4c,0x3,0xc8,0x4c,0x89,0x4a,0x20,0xf,0xb6,0x41,0x5d,0x24,0x1,0x41,0x88,0,0xc3};
    if (std::memcmp(reinterpret_cast<void*>(base + 0x1393330), dispatcher, sizeof(dispatcher)) ||
        std::memcmp(reinterpret_cast<void*>(base + 0x332bb90), actor_dispatcher, sizeof(actor_dispatcher)) ||
        std::memcmp(reinterpret_cast<void*>(base + 0x333be80), thunk, sizeof(thunk))) return 12;
    uint64_t object = fixed_slot(base, packet->object_index, packet->object_serial);
    uint64_t function = fixed_slot(base, packet->function_index, packet->function_serial);
    if (!object || !function) return 13;
    uint64_t cls = local_read<uint64_t>(object + 0x10);
    uint64_t fn_cls = local_read<uint64_t>(function + 0x10);
    if (!exact_name(base, object + 0x18, "Default__Actor") || !(local_read<uint32_t>(object + 8) & 0x10) ||
        !exact_name(base, cls + 0x18, "Actor") || !exact_name(base, fn_cls + 0x18, "Function") ||
        !exact_name(base, function + 0x18, "IsActorBeingDestroyed") || local_read<uint64_t>(function + 0x20) != cls) return 14;
    uint64_t prop = local_read<uint64_t>(function + 0x50);
    if (!prop || !exact_name(base, prop + 0x20, "ReturnValue") ||
        !exact_name(base, local_read<uint64_t>(prop + 8), "BoolProperty") ||
        local_read<uint64_t>(prop + 0x10) != (function | 1) || local_read<uint64_t>(prop + 0x18) != 0 ||
        local_read<int32_t>(prop + 0x30) != 1 || local_read<int32_t>(prop + 0x34) != 1 ||
        local_read<int32_t>(prop + 0x44) != 0 || local_read<uint32_t>(prop + 0x70) != 0xff010001) return 15;
    if (local_read<uint32_t>(function + 0xb0) != 0x54020401 || local_read<uint16_t>(function + 0xb6) != 1 ||
        local_read<uint16_t>(function + 0xb8) != 0 ||
        local_read<uint64_t>(function + 0xd8) != (allowed_entry ? allowed_entry : base + 0x333be80)) return 16;
    uint64_t dispatch = local_read<uint64_t>(local_read<uint64_t>(object) + 0x268);
    if (dispatch != base + 0x332bb90) return 17;
    uint8_t expected = local_read<uint8_t>(object + 0x5d) & 1;
    uint8_t result = 0xcc; // Detect a skipped dispatch; never substitute the expected value.
    using Dispatch = void(__fastcall*)(void*, void*, void*);
    reinterpret_cast<Dispatch>(dispatch)(reinterpret_cast<void*>(object), reinterpret_cast<void*>(function), &result);
    if (result > 1 || result != expected || (local_read<uint8_t>(object + 0x5d) & 1) != expected ||
        fixed_slot(base, packet->object_index, packet->object_serial) != object ||
        fixed_slot(base, packet->function_index, packet->function_serial) != function) return 18;
    packet->result = result; return 0;
}
inline uint32_t invoke_fixed_guarded(SchedulePacket* packet, uint64_t allowed_entry = 0) {
    // Contain access faults, but do not claim SEH can roll back arbitrary engine state.
    __try { return invoke_fixed_body(packet, allowed_entry); }
    __except(EXCEPTION_EXECUTE_HANDLER) { return 19; }
}
