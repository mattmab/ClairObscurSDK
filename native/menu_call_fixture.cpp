#include "menu_call_contract.h"
#include <cstdio>

static CallPacket plan(MenuCall call) {
    const auto& s=*menu_call_spec(call);
    CallPacket p{};
    p.version=1; p.parameter_size=p.allocation_extent=s.size;
    p.return_offset=s.result; p.function_flags=0x400; p.entry_rva=s.rva;
    p.target={1,2,0x1000}; p.function={3,4,0x2000}; p.field_count=s.count;
    const bool player=call==MenuCall::SetFocus || call==MenuCall::UserFocus;
    unsigned field=0;
    if(player) {
        p.fields[field++]={CallObject,0,8,1,0x80,0,"PlayerController",{5,6,0x3000}};
        p.object_count=1; p.objects[0]={0,{7,8,0x4000}};
    }
    if(call==MenuCall::Add) p.fields[0]={CallInt32,0,4,1,0x80,0,"ZOrder",{}};
    else if(s.result!=65535)
        p.fields[field]={CallBool,s.result,1,1,0x480,0xff010001,"ReturnValue",{}};
    return p;
}
int main() {
    for(uint32_t i=0;i<kMenuCalls;++i) {
        auto op=static_cast<MenuCall>(i);
        auto p=plan(op);
        if(!valid_menu_call(p,op)) return 1;
        ++p.entry_rva; if(valid_menu_call(p,op)) return 2;
        p=plan(op); p.function_flags=0; if(valid_menu_call(p,op)) return 3;
        p=plan(op); p.outcome=CallOutcomeUnknown; if(valid_menu_call(p,op)) return 4;
        for(uint32_t other=0;other<kMenuCalls;++other)
            if(other!=i && valid_menu_call(plan(op),static_cast<MenuCall>(other))) return 5;
    }
    auto p=plan(MenuCall::Add);
    int32_t bad=-1; std::memcpy(p.data,&bad,4);
    if(valid_menu_call(p,MenuCall::Add)) return 6;
    bad=10001; std::memcpy(p.data,&bad,4);
    if(valid_menu_call(p,MenuCall::Add)) return 7;
    p=plan(MenuCall::SetFocus); p.object_count=0;
    if(valid_menu_call(p,MenuCall::SetFocus)) return 8;
    p=plan(MenuCall::SetFocus); p.fields[0].flags|=0x100;
    if(valid_menu_call(p,MenuCall::SetFocus)) return 9;
    p=plan(MenuCall::UserFocus); p.fields[1].bool_encoding=0x01010001;
    if(valid_menu_call(p,MenuCall::UserFocus)) return 10;
    p=plan(MenuCall::KeyboardFocus); p.data[0]=1;
    if(valid_menu_call(p,MenuCall::KeyboardFocus)) return 11;
    std::puts("Menu call contracts: ten operations, cross-operation rejection, malformed inputs and outcomes passed.");
    return 0;
}
