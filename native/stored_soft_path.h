#pragma once
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <string>
#include <vector>

// Exact shipping soft object/class property storage. The first eight bytes are
// opaque cache state: copied for stability, never resolved, decoded or emitted.
struct StoredSoftPathStorage {
    uint64_t cache;
    uint32_t package_id, package_number, asset_id, asset_number;
    uint64_t data;
    int32_t count, capacity;
};
static_assert(sizeof(StoredSoftPathStorage)==40);
struct StoredSoftPathCopy { bool null_path; std::string package,asset,subpath; };

inline void stored_soft_require(bool valid,const char* error) {
    if(!valid)throw std::runtime_error(error);
}
inline std::string stored_soft_utf8(const std::vector<char16_t>& units) {
    std::string result;
    for(size_t i=0;i<units.size();++i) {
        uint32_t code=units[i];
        stored_soft_require(code!=0,"SOFT_SUBPATH_EMBEDDED_NULL");
        if(code>=0xd800 && code<=0xdbff) {
            stored_soft_require(i+1<units.size() && units[i+1]>=0xdc00 && units[i+1]<=0xdfff,"SOFT_SUBPATH_UTF16_INVALID");
            code=0x10000+((code-0xd800)<<10)+(uint32_t(units[++i])-0xdc00);
        } else stored_soft_require(code<0xdc00 || code>0xdfff,"SOFT_SUBPATH_UTF16_INVALID");
        if(code<0x80)result+=char(code);
        else if(code<0x800) {result+=char(0xc0|(code>>6));result+=char(0x80|(code&63));}
        else if(code<0x10000) {result+=char(0xe0|(code>>12));result+=char(0x80|((code>>6)&63));result+=char(0x80|(code&63));}
        else {result+=char(0xf0|(code>>18));result+=char(0x80|((code>>12)&63));result+=char(0x80|((code>>6)&63));result+=char(0x80|(code&63));}
    }
    return result;
}
inline bool stored_soft_ascii(const std::string& value,bool package) {
    if(value.empty() || value.size()>1024)return false;
    if(package && (value[0]!='/' || value.back()=='/' || value.find("//")!=std::string::npos))return false;
    for(const auto ch:value)if(!((ch>='a'&&ch<='z') || (ch>='A'&&ch<='Z') ||
        (ch>='0'&&ch<='9') || ch=='_' || (package && ch=='/')))return false;
    return true;
}

template<class Read,class Name>
StoredSoftPathCopy copy_stored_soft_path(const uint8_t* source,uint64_t address,uint32_t width,
    uint64_t property_vtable_rva,Read read,Name name,size_t& string_budget,bool soft_class=false) {
    const uint64_t expected_vtable=soft_class ? 0x6e12cb8 : 0x6e128d8;
    stored_soft_require(source && width==40 && property_vtable_rva==expected_vtable,"SOFT_PROPERTY_LAYOUT_INVALID");
    StoredSoftPathStorage original{};std::memcpy(&original,source,sizeof(original));
    stored_soft_require(original.count>=0 && original.count<=original.capacity && original.capacity<=1048576,
        "SOFT_SUBPATH_COUNTS_INVALID");
    stored_soft_require(original.count<=4097 && size_t(original.count)<=string_budget,"SOFT_SUBPATH_SIZE_LIMIT");
    string_budget-=size_t(original.count);
    std::vector<char16_t> first(size_t(original.count)),second(size_t(original.count));
    if(original.count) {
        stored_soft_require(original.data>=0x10000 && !(original.data&1) &&
            original.data<=0x7fffffffffffULL-uint64_t(original.count)*2,"SOFT_SUBPATH_DATA_INVALID");
        read(original.data,first.data(),first.size()*2);
        read(original.data,second.data(),second.size()*2);
        stored_soft_require(first==second,"SOFT_SUBPATH_CONTENT_CHANGED");
        stored_soft_require(first.back()==0,"SOFT_SUBPATH_TERMINATOR_INVALID");
        first.pop_back();
    }
    const auto subpath=stored_soft_utf8(first);
    const bool null_package=!original.package_id && !original.package_number;
    const bool null_asset=!original.asset_id && !original.asset_number;
    stored_soft_require(null_package==null_asset && (!null_package || subpath.empty()),"SOFT_NULL_PATH_INVALID");
    std::string package,asset;
    if(!null_package) {
        package=name(original.package_id,original.package_number);
        asset=name(original.asset_id,original.asset_number);
        stored_soft_require(stored_soft_ascii(package,true) && stored_soft_ascii(asset,false),"SOFT_PATH_NAMES_INVALID");
    }
    StoredSoftPathStorage repeated{};read(address,&repeated,sizeof(repeated));
    stored_soft_require(!std::memcmp(&original,&repeated,sizeof(original)),"SOFT_PATH_STORAGE_CHANGED");
    return {null_package,package,asset,subpath};
}
