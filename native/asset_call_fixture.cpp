#include "asset_call_protocol.h"
#include <cassert>
#include <iostream>
int main() {
    RetainedCallPacket p{};
    auto& c=p.call;
    c.version=6; c.parameter_size=c.allocation_extent=48; c.return_offset=40;
    c.function_flags=67249155; c.entry_rva=0x3860130; c.field_count=2;
    c.target=c.function={1,2,0x10000};
    auto& a=c.fields[0]; a.kind=17; a.width=40; a.dimension=1; a.flags=7881299347898496ULL;
    a.constraint={3,4,0x20000}; std::memcpy(a.name,"Asset",6);
    auto& r=c.fields[1]; r.kind=CallObject; r.offset=40; r.width=8; r.dimension=1;
    r.flags=6755468160534400ULL; r.constraint=a.constraint; std::memcpy(r.name,"ReturnValue",12);
    c.data[8]=1; c.data[16]=2;
    assert(!validate_asset_call(p));
    for(unsigned i=0;i<48;++i) {
        if((i>=8&&i<12)||(i>=16&&i<20)) continue;
        auto bad=p; bad.call.data[i]=1; assert(validate_asset_call(bad));
    }
    auto bad=p; bad.call.fields[0].flags|=0x100; assert(validate_asset_call(bad));
    bad=p; bad.call.fields[0].constraint.address++; assert(validate_asset_call(bad));
    bad=p; bad.call.entry_rva++; assert(validate_asset_call(bad));
    bad=p; bad.count=1; assert(validate_asset_call(bad));
    assert(validate_call_packet(p.call,true)); // Old dispatcher never accepts this extension.
    std::cout<<"asset contract guards passed\n";
}
