#pragma once
#include <cstdint>
#include <cstring>

// Bounded sparse envelopes carried in the existing console scratch buffer.
// This is a distinct capability/message version; old runtimes never receive it.
namespace e33_ui {
constexpr uint32_t Capacity=65536, Limit=48, Header=20, Action=112;
inline uint32_t word(const uint8_t* p) { uint32_t n; std::memcpy(&n,p,4); return n; }
inline void put(uint8_t* p,uint32_t n) { std::memcpy(p,&n,4); }
inline bool header(const uint8_t* p,uint32_t size,bool request) {
    return size>=Header && size<=Capacity && word(p)==1 && word(p+4)>0 &&
        word(p+4)<=Limit && word(p+8)==size &&
        (request ? (!word(p+12) && !word(p+16)) : word(p+12)<=word(p+4));
}
inline bool expand(const uint8_t* p,uint32_t size,void* output,uint32_t extent) {
    auto* out=static_cast<uint8_t*>(output);
    std::memset(out,0,extent);
    uint32_t at=0,end=0;
    while(at<size) {
        if(size-at<8) return false;
        const auto offset=word(p+at), count=word(p+at+4); at+=8;
        if(!count || offset<end || offset>extent || count>extent-offset || count>size-at) return false;
        std::memcpy(out+offset,p+at,count); at+=count; end=offset+count;
    }
    return at==size;
}
inline bool compress(const void* input,uint32_t size,uint8_t* out,uint32_t available,uint32_t& written) {
    const auto* p=static_cast<const uint8_t*>(input);
    written=0;
    for(uint32_t at=0;at<size;) {
        while(at<size && !p[at]) ++at;
        if(at==size) break;
        const auto start=at;
        uint32_t end=at+1, zeros=0;
        while(++at<size) {
            if(p[at]) { end=at+1; zeros=0; }
            else if(++zeros==16) break;
        }
        const auto count=end-start;
        if(available-written<8 || count>available-written-8) return false;
        put(out+written,start); put(out+written+4,count);
        std::memcpy(out+written+8,p+start,count); written+=8+count;
    }
    return true;
}
}
