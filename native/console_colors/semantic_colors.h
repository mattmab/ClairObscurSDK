#pragma once
#include <cstddef>
#include <cstdint>
namespace ConsoleRenderClone {
struct Color { float r,g,b,a; };
constexpr Color white{1,1,1,1}, blue{0.25f,0.6f,1,1}, green{0.35f,0.9f,0.45f,1}, muted{0.58f,0.62f,0.68f,1}, yellow{1,0.78f,0.2f,1}, red{1,0.3f,0.3f,1};
inline bool prefix(const wchar_t* text,std::size_t count,const wchar_t* expected) {
 std::size_t i=0;
 for(;expected[i];++i) if(i>=count || text[i]!=expected[i]) return false;
 return i==count || text[i]==0 || text[i]==L' ';
}
inline Color classify(const wchar_t* text,std::size_t count) {
 if(!text || count==0 || count>32768)return white;
 if(prefix(text,count,L"[SDK]") || prefix(text,count,L"[EVENT]"))return blue;
 if(prefix(text,count,L"[OK]") || prefix(text,count,L"[READY]"))return green;
 if(prefix(text,count,L"[INFO]"))return muted;
 if(prefix(text,count,L"[WAIT]") || prefix(text,count,L"[WARN]"))return yellow;
 if(prefix(text,count,L"[ERROR]"))return red;
 return white;
}
enum class Block { InvalidUnwind, ChainedUnwind, HandlerRelocationUnproved, RelocationAndCfgUnproved };
// This intentionally cannot authorize executable memory: no full relocator exists.
inline Block executable_plan(const std::uint8_t* info,std::size_t size) {
 if(!info || size<4 || (info[0]&7)!=1) return Block::InvalidUnwind;
 const auto flags=info[0]>>3;
 const std::size_t aligned=(4+std::size_t(info[2])*2+3)&~std::size_t(3);
 if(size<aligned) return Block::InvalidUnwind;
 if(flags&4) return Block::ChainedUnwind;
 if(flags&3) return size<aligned+4 ? Block::InvalidUnwind : Block::HandlerRelocationUnproved;
 return Block::RelocationAndCfgUnproved;
}
}
