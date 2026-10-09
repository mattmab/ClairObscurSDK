#include "invocation_protocol.h"
#include "retained_call_protocol.h"
#include <cstdio>
#include <limits>
#include <fstream>

static CallPacket baseline() {
    CallPacket p{};
    p.version=1; p.parameter_size=1; p.allocation_extent=8; p.return_offset=65535;
    p.target={1,2,0x1234}; p.function={3,4,0x5678}; p.field_count=1;
    p.fields[0]={CallBool,0,1,1,0x80,0xff010001,"Input",{-1,0,0}};
    p.data[0]=1;
    return p;
}
int main(int argc,char** argv) {
    if(argc==2) {
        CallPacket packet{};
        std::ifstream file(argv[1],std::ios::binary);
        file.read(reinterpret_cast<char*>(&packet),sizeof(packet));
        if(file.gcount()!=sizeof(packet) || file.peek()!=std::char_traits<char>::eof()) return 2;
        auto error=validate_call_packet(packet);
        std::printf("%u\n",error);
        return error ? 1 : 0;
    }
    unsigned checks=0;
    auto check=[&](const CallPacket& p,uint32_t expected) {
        ++checks;
        auto actual=validate_call_packet(p);
        if(actual!=expected) { std::fprintf(stderr,"check %u: expected %u, got %u\n",checks,expected,actual); return false; }
        return true;
    };
    auto p=baseline(); if(!check(p,0)) return 1;
    p.version=2; if(!check(p,300)) return 1;
    p=baseline(); p.fields[0].offset=4096; if(!check(p,301)) return 1;
    p=baseline(); p.fields[0].bool_encoding=0xff000001; if(!check(p,303)) return 1;
    p=baseline(); p.data[0]=2; if(!check(p,307)) return 1;
    p=baseline(); p.fields[0].flags|=0x100; if(!check(p,306)) return 1;
    p=baseline(); p.data[20]=1; if(!check(p,311)) return 1;
    p=baseline(); p.return_offset=0; if(!check(p,310)) return 1;
    p=baseline(); p.fields[0].flags|=0x400; p.return_offset=0; p.data[0]=0; if(!check(p,0)) return 1;
    p=baseline(); p.field_count=2; p.fields[1]=p.fields[0]; std::memcpy(p.fields[1].name,"Second",7);
    if(!check(p,305)) return 1;
    p.fields[0].bool_encoding=0x01010001; p.fields[1].bool_encoding=0x02020001; p.data[0]=3;
    if(!check(p,0)) return 1;
    p=baseline(); p.parameter_size=8; p.fields[0]={CallObject,0,8,1,0x80,0,"Object",{5,6,0x9999}};
    p.data[0]=0; p.object_count=1; p.objects[0]={0,{7,8,0xaaaa}};
    if(!check(p,0)) return 1;
    p.data[0]=1; if(!check(p,309)) return 1;
    p.data[0]=0; p.objects[0].offset=1; if(!check(p,313)) return 1;
    p.objects[0].offset=0; p.object_count=2; p.objects[1]=p.objects[0]; if(!check(p,312)) return 1;
    p.object_count=1; p.fields[0].flags|=0x100; if(!check(p,313)) return 1;
    p=baseline(); p.parameter_size=4; p.fields[0]={CallFloat,0,4,1,0x80,0,"Float",{-1,0,0}};
    float n=std::numeric_limits<float>::infinity(); std::memcpy(p.data,&n,4); if(!check(p,308)) return 1;
    p=baseline(); p.fields[0].dimension=0; if(!check(p,301)) return 1;
    std::printf("%u native packet checks passed; packet bytes=%zu\n",checks,sizeof(CallPacket));
    RetainedCallPacket retained{};
    if(!retained_call_empty(retained)) return 1;
    retained.count=1; if(retained_call_empty(retained)) return 1;
    retained.count=0; retained.leases[127].token=1; if(retained_call_empty(retained)) return 1;
    retained={}; retained.call.field_count=4;
    retained.call.fields[0]={CallObject,0,8,1,0x80,0,"Input",{}};
    retained.call.fields[1]={CallClass,8,8,1,0x480,0,"Return",{}};
    retained.call.fields[2]={CallObject,16,8,3,0x8000180,0,"RefOut",{}};
    retained.call.fields[3]={CallInt32,40,4,1,0x180,0,"ScalarOut",{}};
    if(retained_call_slots(retained.call)!=4) return 1;
    std::printf("Retained envelope: %zu bytes; output/refout selection passed.\n",sizeof(retained));
    return 0;
}
