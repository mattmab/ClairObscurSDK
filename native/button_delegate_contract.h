#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

// Exact Steam23765773 delegate contract, not a portable Unreal layout.
// Proven by button-adapter-table/abi/execute-return and button-execute-safe
// evidence. +0x58 takes RCX=instance, RDX=reply storage, returns that pointer.
// +0x60 takes RCX=instance, builds/destroys its own reply, returns bool in AL.
// +0 is the scalar-deleting destructor: RCX=instance, EDX=flags, RAX=instance.
namespace ButtonDelegateContract {
using Execute = void* (*)(void*,void*);
using ExecuteIfSafe = bool (*)(void*);
using Destroy = void* (*)(void*,uint32_t);
constexpr uint64_t table_rva=0x7382098;
constexpr size_t slot_count=13;
constexpr size_t destroy_slot=0, execute_slot=11, safe_slot=12;
constexpr std::array<uint64_t,slot_count> entries{
    0x1260100,0x13b28b0,0x13b28b0,0x10110d0,0x1ec35b0,0x1ec58b0,
    0x1ec5b90,0x1004490,0x3054a90,0x3054a90,0x3054b10,0x3059490,0x305a2e0
};
using Table=std::array<uint64_t,slot_count>;

inline bool matches(uint64_t base,const Table& observed) {
    if(!base || base>UINT64_MAX-table_rva) return false;
    for(size_t i=0;i<slot_count;++i) if(observed[i]!=base+entries[i]) return false;
    return true;
}
// Call only before publishing the shadow table. The runtime must pin its module
// and keep this table immutable for its process lifetime. This function does not
// write engine memory or certify that supplied callbacks have the required ABI.
inline bool prepare(uint64_t base,const Table& observed,Table& shadow,
                    Destroy destroy,Execute execute,ExecuteIfSafe safe) {
    if(!matches(base,observed) || !destroy || !execute || !safe) return false;
    shadow=observed;
    shadow[destroy_slot]=reinterpret_cast<uint64_t>(destroy);
    shadow[execute_slot]=reinterpret_cast<uint64_t>(execute);
    shadow[safe_slot]=reinterpret_cast<uint64_t>(safe);
    // Clone slots remain engine originals, which reconstruct the original table
    // and copy the untouched original member-function pointer, never this table.
    return true;
}
}
