#pragma once
#include "fixed_invocation.h"

// One controlled creation experiment. No viewport write or console input hook.
inline uint64_t console_find(uint64_t base, const char* name, const char* class_name) {
    uint64_t found = 0;
    int32_t count = local_read<int32_t>(base + 0x9361b84);
    uint64_t chunks = local_read<uint64_t>(base + 0x9361b70);
    if (count < 1 || count > 1000000) return 0;
    for (int32_t index = 0; index < count; ++index) {
        uint64_t chunk = local_read<uint64_t>(chunks + uint64_t(index >> 16)*8);
        uint64_t object = local_read<uint64_t>(chunk + uint64_t(index & 65535)*24);
        if (!object || local_read<int32_t>(object+12) != index) continue;
        uint64_t cls = local_read<uint64_t>(object+0x10);
        if (!cls || !exact_name(base, cls+0x18, class_name)) continue;
        // Null name selects the unique non-default instance of this exact class.
        if (name ? !exact_name(base, object+0x18, name) : (local_read<uint32_t>(object+8)&0x10) != 0) continue;
        if (found) return 0;
        found = object;
    }
    return found;
}
inline uint32_t construct_console_body(SchedulePacket* packet) {
    uint32_t prerequisite = invoke_fixed_body(packet);
    if (prerequisite) return prerequisite;
    uint64_t base = reinterpret_cast<uint64_t>(GetModuleHandleW(nullptr));
    if (local_read<uint8_t>(base+0x9272cfc) || local_read<uint8_t>(base+0x934e968)) return 100;
    const uint8_t thunk[] = {0x40,0x53,0x56,0x57,0x48,0x83,0xec,0x20,0x33,0xff,0x49,0x8b,0xf0,0x48,0x89,0x7c,0x24,0x50,0x48,0x8b,0xda,0xe8,0x16,0x81,0xc0,0xfd,0x48,0x8b,0xcb,0x48,0x39,0x7b};
    if (std::memcmp(reinterpret_cast<void*>(base+0x3744670), thunk, sizeof(thunk))) return 101;
    uint64_t console_cls = console_find(base, "Console", "Class");
    uint64_t library_cls = console_find(base, "GameplayStatics", "Class");
    uint64_t library = console_find(base, "Default__GameplayStatics", "GameplayStatics");
    uint64_t viewport = console_find(base, nullptr, "CustomGameViewportClient");
    // SpawnObject can occur on other classes; select its verified owner explicitly.
    uint64_t function = fixed_slot(base, 18293, 0);
    if (!console_cls || !library_cls || !library || !viewport || !function ||
        !exact_name(base,function+0x18,"SpawnObject") || local_read<uint64_t>(function+0x20)!=library_cls ||
        local_read<uint64_t>(library+0x10)!=library_cls || local_read<uint64_t>(viewport+0x40)!=0) return 102;
    if (local_read<uint32_t>(function+0xb0)!=0x4022403 || local_read<uint16_t>(function+0xb6)!=24 ||
        local_read<uint16_t>(function+0xb8)!=16 || local_read<uint64_t>(function+0xd8)!=base+0x3744670) return 103;
    const char* names[] = {"ObjectClass", "Outer", "ReturnValue"};
    const char* types[] = {"ClassProperty", "ObjectProperty", "ObjectProperty"};
    uint64_t prop = local_read<uint64_t>(function+0x50);
    for (int i=0;i<3;++i) {
        if (!prop || !exact_name(base,prop+0x20,names[i]) ||
            !exact_name(base,local_read<uint64_t>(prop+8),types[i]) ||
            local_read<uint64_t>(prop+0x10)!=(function|1) || local_read<int32_t>(prop+0x30)!=1 ||
            local_read<int32_t>(prop+0x34)!=8 || local_read<int32_t>(prop+0x44)!=i*8) return 104;
        prop=local_read<uint64_t>(prop+0x18);
    }
    if (prop) return 105;
    uint64_t dispatch = local_read<uint64_t>(local_read<uint64_t>(library)+0x268);
    if (dispatch!=base+0x1393330) return 106;
    struct { uint64_t cls, outer, result; } params{console_cls,viewport,0};
    using Dispatch = void(__fastcall*)(void*,void*,void*);
    reinterpret_cast<Dispatch>(dispatch)(reinterpret_cast<void*>(library),reinterpret_cast<void*>(function),&params);
    if (!params.result) return 107;
    // The engine owns this unreferenced specimen; leave normal GC to reclaim it.
    // No SDK callback is stored in it and no native allocation is freed by us.
    if (local_read<uint64_t>(params.result+0x10)!=console_cls || local_read<uint64_t>(params.result+0x20)!=viewport ||
        local_read<uint64_t>(params.result)!=base+0x7818778 || local_read<uint64_t>(viewport+0x40)!=0) return 108;
    int32_t index=local_read<int32_t>(params.result+12);
    int32_t count=local_read<int32_t>(base+0x9361b84);
    if (index<0 || index>=count) return 109;
    uint64_t chunks=local_read<uint64_t>(base+0x9361b70);
    if (local_read<uint64_t>(local_read<uint64_t>(chunks+uint64_t(index>>16)*8)+uint64_t(index&65535)*24)!=params.result) return 110;
    packet->result=params.result;
    return 0;
}
inline uint32_t construct_console_guarded(SchedulePacket* packet) {
    __try { return construct_console_body(packet); }
    __except(EXCEPTION_EXECUTE_HANDLER) { return 119; }
}
