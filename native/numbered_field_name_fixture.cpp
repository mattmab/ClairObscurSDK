#include <cstdint>
#include <cstring>
#include <cassert>
template<class T> T local_read(uint64_t at) { return *reinterpret_cast<const T*>(at); }
bool exact_name(uint64_t,uint64_t at,const char* name) {
    return local_read<uint64_t>(at)==123 && std::strcmp(name,"GeneratedLocal")==0;
}
#include "numbered_field_name.h"
int main() {
    uint32_t words[]={123,2};const auto at=reinterpret_cast<uint64_t>(words);
    assert(exact_field_name(0,at,"GeneratedLocal",2));
    assert(!exact_field_name(0,at,"GeneratedLocal"));
    assert(!exact_field_name(0,at,"GeneratedLocal",1));
    assert(!exact_field_name(0,at,"GeneratedLocal_1",2));
    words[0]=124;assert(!exact_field_name(0,at,"GeneratedLocal",2));
    words[0]=123;words[1]=0;assert(exact_field_name(0,at,"GeneratedLocal"));
    assert(!exact_field_name(0,at,"GeneratedLocal",2));
}
