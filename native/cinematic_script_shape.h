#pragma once
#include <cstdint>
#include <cstddef>
namespace e33_cinematic {
template<class Reader, size_t N, size_t M>
bool exact_script_shape(Reader&& read,uint64_t address,const uint8_t (&bytes)[N],
                        const uint32_t (&offsets)[M],const uint64_t (&values)[M]) {
    if(!address || address>UINT64_MAX-N) return false;
    for(size_t i=0;i<M;++i) {
        if(!values[i] || offsets[i]>N || N-offsets[i]<8) return false;
        for(size_t j=0;j<i;++j)
            if(offsets[i]<offsets[j]+8 && offsets[j]<offsets[i]+8) return false;
        uint64_t actual{};
        if(!read(address+offsets[i],&actual,8) || actual!=values[i]) return false;
    }
    for(size_t i=0;i<N;++i) {
        bool pointer=false;
        for(size_t j=0;j<M;++j) if(i>=offsets[j] && i<offsets[j]+8) pointer=true;
        if(pointer) continue;
        uint8_t actual{};
        if(!read(address+i,&actual,1) || actual!=bytes[i]) return false;
    }
    return true;
}
}
