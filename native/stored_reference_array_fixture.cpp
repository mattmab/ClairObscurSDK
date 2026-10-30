#include "stored_reference_array.h"
#include "stored_frame_range.h"
#include <cassert>
#include <iostream>
#include <string>

int main() {
    uint8_t frame_bytes[16]{};frame_bytes[0]=1;
    int32_t lower=-24000,upper=48000;
    std::memcpy(frame_bytes+4,&lower,4);std::memcpy(frame_bytes+12,&upper,4);
    auto range=copy_stored_frame_range(frame_bytes,16);
    assert(range.lower_kind==1 && range.lower==-24000 && range.upper_kind==0 && range.upper==48000);
    frame_bytes[0]=2;frame_bytes[8]=2;
    range=copy_stored_frame_range(frame_bytes,16);assert(range.lower==0 && range.upper==0);
    frame_bytes[0]=3;
    try {copy_stored_frame_range(frame_bytes,16);assert(false);}
    catch(const std::runtime_error& error){assert(std::string(error.what())=="FRAME_RANGE_KIND_INVALID");}
    StoredReferenceArrayHeader header{0x20000,65,65};
    std::vector<uint64_t> items(65,0x30000);
    unsigned content_reads=0;bool change_content=false,change_header=false;
    auto read=[&](uint64_t at,void* target,size_t size) {
        if(at==0x10000) {
            auto copy=header;if(change_header)++copy.count;
            std::memcpy(target,&copy,size);
        } else {
            assert(at==header.data && size<=items.size()*8);
            std::memcpy(target,items.data(),size);
            if(change_content && ++content_reads==2)static_cast<uint64_t*>(target)[0]++;
        }
    };
    auto run=[&](){size_t budget=100;return copy_stored_reference_array(
        reinterpret_cast<uint8_t*>(&header),0x10000,read,budget);};
    auto rejects=[&](const char* error) {
        try {run();assert(false);} catch(const std::runtime_error& failure) {assert(failure.what()==std::string(error));}
        content_reads=0;size_t generic_budget=100;
        try {copy_stored_array_bytes(reinterpret_cast<uint8_t*>(&header),0x10000,4,read,generic_budget);assert(false);}
        catch(const std::runtime_error& failure) {assert(failure.what()==std::string(error));}
    };
    auto result=run();assert(result.total==65 && result.items.size()==64);
    size_t scalar_budget=100;
    auto scalar=copy_stored_array_bytes(reinterpret_cast<uint8_t*>(&header),0x10000,4,read,scalar_budget);
    assert(scalar.total==65 && scalar.bytes.size()==256 && scalar_budget==36);
    scalar_budget=100;
    try {copy_stored_array_bytes(reinterpret_cast<uint8_t*>(&header),0x10000,513,read,scalar_budget);assert(false);}
    catch(const std::runtime_error& error){assert(std::string(error.what())=="STRUCT_ARRAY_ELEMENT_SIZE_LIMIT");}
    change_content=true;rejects("STRUCT_ARRAY_CONTENT_CHANGED");change_content=false;
    change_header=true;rejects("STRUCT_ARRAY_HEADER_CHANGED");change_header=false;
    header.count=-1;rejects("STRUCT_ARRAY_COUNTS_INVALID");header.count=65;
    header.data=3;rejects("STRUCT_ARRAY_DATA_INVALID");header.data=0x20000;
    size_t budget=63;
    try {copy_stored_reference_array(reinterpret_cast<uint8_t*>(&header),0x10000,read,budget);assert(false);}
    catch(const std::runtime_error& error){assert(std::string(error.what())=="STRUCT_ARRAY_NODE_LIMIT");}
    header.count=header.capacity=0;header.data=0;
    assert(run().items.empty());
    std::cout<<"Stored reference arrays: stability, bounds and partial prefix PASS\n";
}
