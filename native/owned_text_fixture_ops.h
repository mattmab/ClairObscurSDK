#pragma once
#include "owned_text_value.h"
#include <map>
#include <stdexcept>
#include <vector>

struct FakeTextOps {
    bool context=true, known=true, fail_construct=false, fail_read=false, fail_release=false;
    bool invalid_header=false, unreadable=false;
    unsigned constructions=0, releases=0, reads=0;
    unsigned fail_construct_at=0, fail_release_at=0;
    uint64_t next=1;
    std::map<uint64_t,std::vector<uint16_t>> values;
    bool can_create() const { return context; }
    bool can_release() const { return context; }
    bool known_text(const TargetTextValue& value) const {
        return known && value.flags==2 && values.count(value.data)==1;
    }
    void construct(TargetTextValue& result,const TargetStringValue& input) {
        ++constructions;
        const auto source=reinterpret_cast<const uint16_t*>(input.data);
        result={next++,2,0};
        values[result.data]={source,source+input.count};
        if(fail_construct || constructions==fail_construct_at) throw std::runtime_error("Fault after allocation");
    }
    TargetStringValue display_string(TargetTextValue& value) {
        ++reads;
        if(fail_read) throw std::runtime_error("Fault during display refresh");
        if(invalid_header) return {0,4,3};
        const auto& units=values.at(value.data);
        if(units.size()==1) return {}; // The engine's default empty string.
        return {reinterpret_cast<uint64_t>(units.data()),static_cast<int32_t>(units.size()),
                static_cast<int32_t>(units.size())};
    }
    bool read_units(uint64_t address,uint16_t* output,uint32_t units) {
        if(unreadable) return false;
        std::memcpy(output,reinterpret_cast<const void*>(address),units*sizeof(uint16_t));
        return true;
    }
    void release(TargetTextValue& value) {
        ++releases;
        values.erase(value.data);
        if(fail_release || releases==fail_release_at) throw std::runtime_error("Fault after releasing");
    }
};
