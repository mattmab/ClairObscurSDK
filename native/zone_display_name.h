#pragma once
#include <string>

// Compare the full displayed FName, including Unreal's number-minus-one suffix.
// Keep exact_name's zero-number rule for all fixed class/function profiles.
inline bool zone_display_name(uint64_t base,uint64_t at,const char* expected) {
 const auto number=local_read<uint32_t>(at+4);
 if(!number)return exact_name(base,at,expected);
 const std::string suffix="_"+std::to_string(number-1),full(expected);
 if(full.size()<=suffix.size() || full.compare(full.size()-suffix.size(),suffix.size(),suffix)!=0)return false;
 const auto prefix=full.substr(0,full.size()-suffix.size());
 const uint64_t unnumbered=local_read<uint32_t>(at);
 return exact_name(base,reinterpret_cast<uint64_t>(&unnumbered),prefix.c_str());
}
