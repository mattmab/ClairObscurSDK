#include "../../native/stored_bool_array.h"
#include <cassert>
#include <initializer_list>
int main(){
 assert(stored_native_bool_layout(1,0xff010001U));
 for(int width:{0,2,4,8,16})assert(!stored_native_bool_layout(width,0xff010001U));
 for(uint32_t encoding:{0U,0x01010001U,0x02020001U,0xff010101U,0xff000001U,0xff010002U})assert(!stored_native_bool_layout(1,encoding));
 for(unsigned value=0;value<256;++value)assert(stored_native_bool_value(uint8_t(value))==(value!=0));
}
