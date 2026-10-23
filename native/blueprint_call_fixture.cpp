#include "blueprint_call_protocol.h"
#include <cstdio>

int main() {
    CallPacket p{};
    p.version=kBlueprintCallVersion;p.return_offset=65535;
    p.function_flags=0x0c020000;p.entry_rva=kBlueprintThunkRva;
    p.target={1,2,0x1234};p.function={3,4,0x5678};
    if(validate_blueprint_call(p) || validate_call_packet(p,true)!=300)return 1;
    for(unsigned bit=0;bit<32;++bit)if(kBlueprintForbiddenFlags&(1u<<bit)) {
        auto bad=p;bad.function_flags|=1u<<bit;
        if(validate_blueprint_call(bad)!=1470)return 2;
    }
    if(blueprint_function_admitted(p.function_flags,p.entry_rva,"ExecuteUbergraph_QA") ||
       blueprint_function_admitted(p.function_flags,0x1234,"ResetState"))return 3;
    // Pure getter: zero initialized boolean return and exact return offset.
    p.parameter_size=p.allocation_extent=1;p.return_offset=0;p.field_count=1;
    p.fields[0]={CallBool,0,1,1,0x480,0xff010001,"ReturnValue",{-1,0,0}};
    if(validate_blueprint_call(p))return 4;
    p.data[0]=1;if(validate_blueprint_call(p)!=306)return 5;
    p.data[0]=0;p.fields[0].offset=1;if(validate_blueprint_call(p)!=301)return 6;
    p.fields[0].offset=0;p.fields[0].kind=CallQualifiedFrameTime;
    if(validate_blueprint_call(p)!=1471)return 7;
    // Object inputs remain identity patches; pointers cannot be supplied as data.
    p.parameter_size=p.allocation_extent=8;p.return_offset=65535;
    p.fields[0]={CallObject,0,8,1,0x80,0,"Target",{5,6,0x9999}};
    p.object_count=1;p.objects[0]={0,{7,8,0xaaaa}};
    if(validate_blueprint_call(p))return 8;
    p.data[0]=1;if(validate_blueprint_call(p)!=309)return 9;
    // FName strings are in the bounded identifier tail; raw IDs stay forbidden.
    p.data[0]=0;p.object_count=0;p.fields[0]={kBlueprintNameKind,0,8,1,0x80,0,"QuestName",{-1,0,0}};
    std::memcpy(p.fields[0].name+10,"Quests_LumiereAct1",18);
    if(validate_blueprint_call(p))return 10;
    p.data[0]=1;if(validate_blueprint_call(p)!=1473)return 11;
    p.data[0]=0;p.fields[0].flags|=0x100;if(validate_blueprint_call(p)!=1473)return 12;
    p.fields[0].flags=0x8001048000394ull;
    if(validate_blueprint_call(p))return 13;
    p.fields[0].flags|=0x400;if(validate_blueprint_call(p)!=1473)return 14;
    p.parameter_size=p.allocation_extent=16;p.return_offset=65535;p.field_count=1;
    p.fields[0]={CallGuid,0,16,1,0x8001048000396ull,0,"DialogueGUID",{5,0,0x9999}};
    int32_t words[]={1339984714,1236766104,-1170703726,625081477};std::memcpy(p.data,words,16);
    if(validate_blueprint_call(p))return 15;
    auto bad=p;bad.fields[0].width=8;if(!validate_blueprint_call(bad))return 16;
    std::puts("Blueprint v8 opt-in, zeroarg/getter, forbidden flags, schema and identity patch checks passed.");
}
