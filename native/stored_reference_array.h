#pragma once
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <vector>
#include <utility>

// The same ordinary TArray storage as the top-level reflected array reader.
// Copy only a bounded prefix; never emit its backing pointer or own allocation.
struct StoredReferenceArrayHeader { uint64_t data; int32_t count,capacity; };
static_assert(sizeof(StoredReferenceArrayHeader)==16);
struct StoredReferenceArrayCopy { int32_t total; std::vector<uint64_t> items; };
struct StoredArrayBytes { int32_t total;std::vector<uint8_t> bytes; };
template<class Read>
StoredArrayBytes copy_stored_array_bytes(const uint8_t* source,uint64_t at,
    size_t width,Read read,size_t& budget) {
    auto check=[](bool ok,const char* error){if(!ok)throw std::runtime_error(error);};
    check(width && width<=512,"STRUCT_ARRAY_ELEMENT_SIZE_LIMIT");
    StoredReferenceArrayHeader first{};std::memcpy(&first,source,sizeof(first));
    check(first.count>=0 && first.capacity>=first.count && first.capacity<=1048576,
          "STRUCT_ARRAY_COUNTS_INVALID");
    const size_t count=first.count>64 ? 64 : size_t(first.count);
    check(count<=budget,"STRUCT_ARRAY_NODE_LIMIT");budget-=count;
    std::vector<uint8_t> items(count*width),again(count*width);
    if(count) {
        check(first.data>=0x10000 && !(first.data&1) &&
              first.data<=0x7fffffffffffULL-items.size(),"STRUCT_ARRAY_DATA_INVALID");
        read(first.data,items.data(),items.size());
        read(first.data,again.data(),again.size());
        check(items==again,"STRUCT_ARRAY_CONTENT_CHANGED");
    }
    StoredReferenceArrayHeader last{};read(at,&last,sizeof(last));
    check(!std::memcmp(&first,&last,sizeof(first)),"STRUCT_ARRAY_HEADER_CHANGED");
    return {first.count,std::move(items)};
}
template<class Read>
StoredReferenceArrayCopy copy_stored_reference_array(const uint8_t* source,uint64_t at,
    Read read,size_t& budget) {
    auto check=[](bool ok,const char* error){if(!ok)throw std::runtime_error(error);};
    StoredReferenceArrayHeader first{};std::memcpy(&first,source,sizeof(first));
    check(first.count>=0 && first.capacity>=first.count && first.capacity<=1048576,
          "STRUCT_ARRAY_COUNTS_INVALID");
    const size_t count=first.count>64 ? 64 : size_t(first.count);
    check(count<=budget,"STRUCT_ARRAY_NODE_LIMIT");budget-=count;
    std::vector<uint64_t> items(count),again(count);
    if(count) {
        check(first.data>=0x10000 && !(first.data&7) &&
              first.data<=0x7fffffffffffULL-count*8,"STRUCT_ARRAY_DATA_INVALID");
        read(first.data,items.data(),count*8);
        read(first.data,again.data(),count*8);
        check(items==again,"STRUCT_ARRAY_CONTENT_CHANGED");
    }
    StoredReferenceArrayHeader last{};read(at,&last,sizeof(last));
    check(!std::memcmp(&first,&last,sizeof(first)),"STRUCT_ARRAY_HEADER_CHANGED");
    return {first.count,std::move(items)};
}
