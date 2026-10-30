#pragma once
#include <cstdint>
#include <cstring>
#include <cstdio>

// Observe existing FName entries only. Never create a name or treat an arbitrary
// suffix as a pointer. Conservative bounds cover signed external name numbers.
inline bool asset_split_number(const char* text,char* base,size_t capacity,uint32_t& number) {
    if(!text||!base||!capacity)return false;
    const auto length=std::strlen(text);
    if(!length||length>=capacity)return false;
    std::memcpy(base,text,length+1);number=0;
    const char* suffix=std::strrchr(text,'_');
    if(!suffix||suffix==text||!suffix[1]||(suffix[1]=='0'&&suffix[2]))return true;
    uint64_t value=0;
    for(const char* at=suffix+1;*at;++at) {
        if(*at<'0'||*at>'9')return true;
        value=value*10+static_cast<unsigned>(*at-'0');
        if(value>=0x7fffffffULL)return true;
    }
    base[suffix-text]=0;number=static_cast<uint32_t>(value)+1;return true;
}
inline bool asset_append_number(char* text,size_t capacity,uint32_t number) {
    if(!number)return true;
    if(!text||number>0x7fffffffU)return false;
    const auto length=std::strlen(text);
    if(length>=capacity)return false;
    const auto count=std::snprintf(text+length,capacity-length,"_%u",number-1);
    return count>0&&static_cast<size_t>(count)<capacity-length;
}
