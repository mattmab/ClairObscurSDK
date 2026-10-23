#pragma once
#include <cstdint>
namespace e33_console_color {
constexpr std::uint32_t Action=138,Version=1;
struct Packet {std::uint32_t version=Version,native_version=0,bound=0,disabled=0,unsupported=0,reserved=0;std::uint64_t frames=0,fallbacks=0,faults=0;};
static_assert(sizeof(Packet)==48,"Console status uses existing scratch only");
inline bool valid(const Packet& p){return p.version==Version && !p.native_version && !p.bound && !p.disabled && !p.unsupported && !p.reserved && !p.frames && !p.fallbacks && !p.faults;}
}
