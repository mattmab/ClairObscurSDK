#include "text_call_protocol.h"
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <cstdlib>

static void specimen(TextCallPacket& p) {
    p={};
    auto& call=p.retained.call;
    call.version=3; call.parameter_size=call.allocation_extent=32;
    call.return_offset=16; call.function_flags=0x400;
    call.target={1,2,0x1234}; call.function={3,4,0x5678}; call.field_count=2;
    call.fields[0]={kTextCallKind,0,16,1,0x80,0,"Input",{-1,0,0}};
    call.fields[1]={kTextCallKind,16,16,1,0x480,0,"ReturnValue",{-1,0,0}};
    p.count=2;
    p.texts[0].count=2; p.texts[0].units[0]='A';
    p.texts[1].field_index=1;
}

int main(int argc,char** argv) {
    if(argc==2) {
        TextCallPacket p{};
        std::ifstream file(argv[1],std::ios::binary);
        file.read(reinterpret_cast<char*>(&p),sizeof(p));
        if(file.gcount()!=sizeof(p) || file.peek()!=std::char_traits<char>::eof()) return 2;
        auto error=validate_text_call(p);
        std::cout << error << '\n'; return error ? 1 : 0;
    }
    unsigned checks=0;
    auto check=[&](const TextCallPacket& p,uint32_t expected) {
        ++checks; auto actual=validate_text_call(p);
        if(actual!=expected) {
            std::cerr << "Text wire check " << checks << ": expected " << expected << ", got " << actual << std::endl;
            std::exit(1);
        }
    };
    TextCallPacket p{}; specimen(p); check(p,0);
    if(validate_call_packet(p.retained.call,true)!=300) return 1;
    p.version=2; check(p,600);
    specimen(p); p.retained.call.version=2; check(p,601);
    specimen(p); p.count=9; check(p,600);
    specimen(p); p.retained.count=1; check(p,600);
    specimen(p); p.retained.call.fields[0].width=8; check(p,602);
    specimen(p); p.retained.call.fields[0].dimension=2; check(p,602);
    specimen(p); p.retained.call.fields[0].constraint.address=1; check(p,602);
    specimen(p); p.retained.call.data[0]=1; check(p,603);
    specimen(p); p.texts[0].field_index=1; check(p,604);
    specimen(p); p.texts[0].count=0; check(p,605);
    specimen(p); p.texts[0].units[0]=0xd800; check(p,605);
    specimen(p); p.texts[0].units[1]='B'; check(p,605);
    specimen(p); p.texts[0].units[2]='X'; check(p,606);
    specimen(p); p.texts[1].count=1; check(p,605);
    specimen(p); p.count=3; check(p,607);
    specimen(p); p.retained.call.return_offset=0; check(p,608);
    specimen(p); p.texts[2].count=1; check(p,609);
    specimen(p); p.retained.call.fields[0].offset=16; check(p,305);
    specimen(p); p.retained.call.fields[0].flags|=0x400; p.texts[0].count=0; p.texts[0].units[0]=0; check(p,608);
    specimen(p); p.texts[0].count=kOwnedTextUnits;
    for(uint32_t i=0;i<kOwnedTextUnits-1;++i) p.texts[0].units[i]='a';
    check(p,0);
    p.texts[0].count=kOwnedTextUnits+1; check(p,604);
    std::cout << checks << " text envelope checks passed; v11 rejects candidate packets.\n";
}
