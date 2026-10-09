#define NOMINMAX
#include <Windows.h>
#include "target_owned_text.h"
#include <iostream>

int main() {
    // Synthetic readable memory tests the actual adapter predicate only. No
    // function pointer is called and no live engine allocation is involved.
    uint64_t table[6]{};
    const auto base=reinterpret_cast<uint64_t>(table)-0x6da8c78;
    table[0]=base+0x10abe30; table[1]=base+0x10acdb0;
    table[2]=base+0x10cbce0; table[5]=base+0x10baa50;
    struct Data { uint64_t table; int32_t refs; uint32_t padding; };
    Data data{reinterpret_cast<uint64_t>(table),1,0};
    TargetOwnedTextOps ops{base};
    TargetTextValue value{reinterpret_cast<uint64_t>(&data),0,0};
    if(!ops.known_text(value)) return 1;
    value.flags=2;
    if(!ops.known_text(value)) return 2;
    value.flags=1;
    if(ops.known_text(value)) return 3;
    value.flags=3;
    if(ops.known_text(value)) return 4;
    value.flags=2; value.padding=1;
    if(ops.known_text(value)) return 5;
    value.padding=0; data.refs=0;
    if(ops.known_text(value)) return 6;
    data.refs=-1;
    if(ops.known_text(value)) return 7;
    data.refs=1;
    for(const auto index:{0,1,2,5}) {
        const auto saved=table[index]; table[index]=0;
        if(ops.known_text(value)) return 8+index;
        table[index]=saved;
    }
    data.table=0;
    if(ops.known_text(value)) return 14;
    value.data=0;
    if(ops.known_text(value)) return 15;
    std::cout << "13 actual target text-type predicate checks passed on synthetic memory.\n";
}
