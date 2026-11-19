#pragma once
#include <cstdint>
// UE native bool arrays are byte-strided. Packed bool masks and relative
// allocator arrays remain unsupported; no bit-packed storage is inferred.
inline bool stored_native_bool_layout(int element_size,uint32_t encoding){return element_size==1&&encoding==0xff010001U;}
inline bool stored_native_bool_value(uint8_t value){return value!=0;}
