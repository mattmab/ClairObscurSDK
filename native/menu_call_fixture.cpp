#include "menu_call_contract.h"
#include "menu_protocol.h"
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
    // Static storage mirrors the native envelope without a large stack frame.
    static MenuPacket wire{};
    wire.version=1; wire.operation=static_cast<uint32_t>(MenuOperation::Prepare);
    wire.owner=2; wire.widget_lease=3; wire.child_lease=4;
    wire.engine=wire.widget=wire.child=wire.player=wire.library={1,2,0x1000};
    for(uint32_t i=0;i<kMenuCalls;++i) wire.plans[i]=plan(static_cast<MenuCall>(i));
    if(!valid_menu_request(wire)) return 12;
    wire.child_lease=3; if(valid_menu_request(wire)) return 13;
    wire.child_lease=4; wire.outcome=1; if(valid_menu_request(wire)) return 14;
    wire.outcome=0; wire.engine.index=-1; if(valid_menu_request(wire)) return 15;
    wire.engine.index=1; wire.plans[8].entry_rva=0; if(valid_menu_request(wire)) return 16;
    wire.operation=static_cast<uint32_t>(MenuOperation::Close);
    if(!valid_menu_request(wire)) return 17; // Close never consumes preparation plans.
    wire.owner=0; if(valid_menu_request(wire)) return 18;
    wire.owner=2; wire.operation=6; if(valid_menu_request(wire)) return 19;
    std::puts("Menu call contracts: ten operations, cross-operation rejection, malformed inputs and outcomes passed.");
    std::puts("Menu envelope: owner, operation, identity, lease and preparation-plan validation passed.");
    return 0;
}
