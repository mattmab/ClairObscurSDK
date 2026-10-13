#include "asset_call_protocol.h"
#include "picto_progression_protocol.h"
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
    auto cls=p;cls.call.entry_rva=0x3860250;cls.call.fields[1].kind=CallClass;
    std::memset(cls.call.fields[0].name,0,96);std::memcpy(cls.call.fields[0].name,"AssetClass",11);
    assert(!validate_asset_call(cls));
    bad=cls;bad.call.fields[1].kind=CallObject;assert(validate_asset_call(bad));
    bad=cls;bad.call.entry_rva=0x3860130;assert(validate_asset_call(bad));
    PictoProgressionPacket pp{};pp.operation=1;pp.target=pp.function=pp.panel={1,2,0x1000};pp.expected=33;pp.value=32;
    assert(valid_picto_progression(pp));
    auto badp=pp;badp.value=34;assert(!valid_picto_progression(badp));
    badp=pp;badp.value=0;assert(!valid_picto_progression(badp));
    badp=pp;badp.outcome=1;assert(!valid_picto_progression(badp));
    pp.operation=2;pp.source=pp.game_instance={3,4,0x2000};pp.expected=4;pp.value=0;
    assert(valid_picto_progression(pp));
    badp=pp;badp.source.address=0;assert(!valid_picto_progression(badp));
    badp=pp;badp.value=101;assert(!valid_picto_progression(badp));
    pp.expected=246;assert(valid_picto_progression(pp));
    pp.expected=2147483647;assert(valid_picto_progression(pp));
    pp.operation=3;pp.expected=101;assert(!valid_picto_progression(pp));
    pp.operation=3;pp.expected=40;pp.value=0;assert(valid_picto_progression(pp));
    badp=pp;badp.expected=-1;assert(!valid_picto_progression(badp));
    badp=pp;badp.value=101;assert(!valid_picto_progression(badp));
    badp=pp;badp.observed=40;assert(!valid_picto_progression(badp));
    badp=pp;badp.game_instance.address=0;assert(!valid_picto_progression(badp));
    badp=pp;badp.operation=4;assert(!valid_picto_progression(badp));
    pp.operation=6;pp.panel={};assert(valid_picto_progression(pp));
    badp=pp;badp.panel.serial=1;assert(!valid_picto_progression(badp));
    badp=pp;badp.operation=9;assert(!valid_picto_progression(badp));
    pp.operation=5;pp.expected=2147483647;assert(valid_picto_progression(pp));
    pp.operation=4;pp.expected=33;pp.value=32;pp.source={};pp.game_instance={};assert(valid_picto_progression(pp));
    badp=pp;badp.value=34;assert(!valid_picto_progression(badp));
    pp.operation=9;pp.expected=249;pp.value=6;pp.panel={};pp.source={};pp.game_instance={};
    assert(valid_picto_progression(pp));
    badp=pp;badp.value=2;assert(!valid_picto_progression(badp));
    badp=pp;badp.expected=-1;assert(!valid_picto_progression(badp));
    badp=pp;badp.source.address=0x1000;assert(!valid_picto_progression(badp));
    badp=pp;badp.panel.address=0x1000;assert(!valid_picto_progression(badp));
    pp.operation=1;pp.expected=33;pp.value=32;pp.panel={1,2,0x1000};
    pp={};pp.operation=10;pp.target=pp.function=pp.source=pp.panel=pp.game_instance={1,2,0x1000};pp.value=1;
    assert(valid_picto_progression(pp));
    badp=pp;badp.expected=2;assert(!valid_picto_progression(badp));
    badp=pp;badp.value=-1;assert(!valid_picto_progression(badp));
    badp=pp;badp.panel={};assert(!valid_picto_progression(badp));
    badp=pp;badp.source={};assert(!valid_picto_progression(badp));
    pp.operation=11;pp.value=0;pp.panel={};pp.game_instance={};assert(valid_picto_progression(pp));
    badp=pp;badp.value=1;assert(!valid_picto_progression(badp));
    badp=pp;badp.panel={1,2,0x1000};assert(!valid_picto_progression(badp));
    std::cout<<"asset contract guards passed\n";
}
