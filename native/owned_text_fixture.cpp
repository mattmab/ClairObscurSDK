#include "owned_text_value.h"
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <vector>

#include "owned_text_fixture_ops.h"


int main() {
    static_assert(!std::is_copy_constructible_v<OwnedTextStorage>);
    static_assert(!std::is_move_constructible_v<OwnedTextStorage>);
    unsigned checks=0;
    auto check=[&](bool condition) { ++checks; if(!condition) throw std::runtime_error("Check "+std::to_string(checks)); };
    using R=OwnedTextResult;
    uint16_t input[]{'M','o','d','s',' ',0xd83d,0xde80,0};
    uint16_t output[kOwnedTextUnits]{};
    uint32_t count=0;
    FakeTextOps ops;
    OwnedTextStorage text;
    check(create_owned_text(ops,text,input,8)==R::Ok);
    check(ops.values.size()==1 && text.state==OwnedTextState::Live);
    input[0]='X';
    check(copy_owned_text(ops,text,output,kOwnedTextUnits,count)==R::Ok && count==8 && output[0]=='M');
    check(create_owned_text(ops,text,input,8)==R::Occupied && ops.constructions==1);
    output[0]=123;
    check(copy_owned_text(ops,text,output,2,count)==R::OutputTooSmall && !count && output[0]==123);
    ops.context=false;
    check(copy_owned_text(ops,text,output,kOwnedTextUnits,count)==R::InvalidContext);
    check(release_owned_text(ops,text)==R::ReleaseDeferred && ops.releases==0);
    ops.context=true;
    ops.invalid_header=true;
    check(copy_owned_text(ops,text,output,kOwnedTextUnits,count)==R::InvalidString && !count);
    ops.invalid_header=false;
    ops.unreadable=true;
    check(copy_owned_text(ops,text,output,kOwnedTextUnits,count)==R::InvalidString && !count);
    ops.unreadable=false;
    ops.known=false;
    check(release_owned_text(ops,text)==R::UnsupportedValue && ops.releases==0);
    ops.known=true;
    check(release_owned_text(ops,text)==R::Ok && ops.values.empty());
    check(release_owned_text(ops,text)==R::Ok && ops.releases==1);
    uint16_t empty[]{0};
    check(create_owned_text(ops,text,empty,1)==R::Ok);
    check(copy_owned_text(ops,text,output,kOwnedTextUnits,count)==R::Ok && count==1 && !output[0]);
    check(release_owned_text(ops,text)==R::Ok);
    const auto before=ops.constructions;
    const uint16_t embedded[]{'A',0,'B',0}, high[]{0xd800,0}, low[]{0xdc00,0}, unterminated[]{'A'};
    check(create_owned_text(ops,text,nullptr,0)==R::InvalidInput);
    check(create_owned_text(ops,text,embedded,4)==R::InvalidInput);
    check(create_owned_text(ops,text,high,2)==R::InvalidInput);
    check(create_owned_text(ops,text,low,2)==R::InvalidInput);
    check(create_owned_text(ops,text,unterminated,1)==R::InvalidInput);
    check(create_owned_text(ops,text,input,kOwnedTextUnits+1)==R::InvalidInput);
    check(ops.constructions==before && ops.values.empty());
    ops.context=false;
    check(create_owned_text(ops,text,empty,1)==R::InvalidContext);
    ops.context=true;
    std::vector<uint16_t> maximum(kOwnedTextUnits,'a'); maximum.back()=0;
    check(create_owned_text(ops,text,maximum.data(),kOwnedTextUnits)==R::Ok);
    check(copy_owned_text(ops,text,output,kOwnedTextUnits,count)==R::Ok && count==kOwnedTextUnits);
    check(release_owned_text(ops,text)==R::Ok);

    FakeTextOps unexpected;
    OwnedTextStorage rejected;
    unexpected.known=false;
    check(create_owned_text(unexpected,rejected,empty,1)==R::UnsupportedValue);
    check(rejected.state==OwnedTextState::ConstructionUnknown);
    unexpected.known=true;
    check(release_owned_text(unexpected,rejected)==R::Uncertain && unexpected.releases==0);

    // Inject faults after side effects to verify no implicit retry/double free.
    for(int phase=0;phase<3;++phase) {
        FakeTextOps fault;
        OwnedTextStorage uncertain;
        fault.fail_construct=phase==0;
        try {
            check(create_owned_text(fault,uncertain,input,8)==R::Ok);
            if(phase==1) { fault.fail_read=true; copy_owned_text(fault,uncertain,output,kOwnedTextUnits,count); }
            else if(phase==2) { fault.fail_release=true; release_owned_text(fault,uncertain); }
            throw std::logic_error("Expected injected fault");
        } catch(const std::runtime_error&) {}
        const auto creates=fault.constructions, destroys=fault.releases, reads=fault.reads;
        check(create_owned_text(fault,uncertain,input,8)==R::Uncertain);
        check(copy_owned_text(fault,uncertain,output,kOwnedTextUnits,count)==R::Uncertain);
        check(release_owned_text(fault,uncertain)==R::Uncertain);
        check(creates==fault.constructions && destroys==fault.releases && reads==fault.reads);
    }
    std::cout << checks << " owned-text input/copy/lifecycle/fault checks passed; no engine function executed.\n";
}
