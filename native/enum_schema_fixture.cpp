#include "target_pod_schema.h"
#include "enum_schema.h"
#include "enum_call_protocol.h"
#include <map>
#include <string>
#include <iostream>
#include <stdexcept>
#include <fstream>

bool compile_enum_adapter(uint64_t base,uint64_t property,const CallIdentity& id,uint8_t value) {
    TargetPodSchemaOps ops{base};
    return validate_byte_enum_value(ops,property,id,value);
}

struct Memory {
    uint64_t base=0x140000000ULL;
    std::map<uint64_t,uint64_t> words;
    std::map<uint64_t,std::string> names;
    std::map<uint64_t,CallIdentity> objects;
    unsigned calls=0, stop_after=100;
    bool context() { return ++calls<=stop_after; }
    template<class T> T read(uint64_t at) { return static_cast<T>(words.at(at)); }
    bool name(uint64_t at,const char* expected) { return names.count(at) && names.at(at)==expected; }
    CallIdentity capture(uint64_t at) { return objects.count(at) ? objects.at(at) : CallIdentity{-1,0,0}; }
    bool identity(const CallIdentity& id) {
        auto current=capture(id.address);
        return id.address && current.address==id.address && current.index==id.index && current.serial==id.serial;
    }
    void object(uint64_t at,const char* name,uint64_t cls,uint64_t outer) {
        objects[at]={static_cast<int32_t>(objects.size()),17,at};
        words[at+8]=0; words[at+0x10]=cls; words[at+0x20]=outer; names[at+0x18]=name;
    }
};
struct Fixture {
    Memory m;
    uint64_t property=0x10000,child=0x11000,enumeration=0x12000,cls=0x13000,
             package=0x14000,package_class=0x15000,data=0x16000;
    CallIdentity id{};
    Fixture() {
        m.object(package_class,"Package",0,0);
        m.object(package,"/Script/CoreUObject",package_class,0);
        m.object(cls,"Enum",0,package);
        m.object(enumeration,"Example",cls,package);
        id=m.capture(enumeration);
        m.words[enumeration]=m.base+0x6dee0b0;
        m.words[enumeration+0x40]=data; m.words[enumeration+0x48]=3; m.words[enumeration+0x4c]=3;
        m.words[data+8]=0; m.words[data+24]=2; m.words[data+40]=255;
        m.words[property]=m.base+0x6deeee8;
        m.words[property+8]=0x17000; m.names[0x17000]="EnumProperty";
        m.words[property+0x30]=1; m.words[property+0x34]=1;
        m.words[property+0x70]=child; m.words[property+0x78]=enumeration;
        m.words[child+8]=0x18000; m.names[0x18000]="ByteProperty";
        m.words[child+0x10]=property; m.words[child+0x30]=1; m.words[child+0x34]=1;
        m.words[child+0x44]=0; m.words[child+0x70]=0;
    }
    bool check(uint8_t value=2) { return validate_byte_enum_value(m,property,id,value); }
};
int main(int argc,char** argv) {
    try {
        if(argc==2) {
            std::ifstream file(argv[1],std::ios::binary|std::ios::ate);
            if(!file || file.tellg()!=static_cast<std::streamoff>(sizeof(RetainedCallPacket))) return 10;
            RetainedCallPacket input{};
            file.seekg(0); file.read(reinterpret_cast<char*>(&input),sizeof(input));
            if(!file || validate_enum_call(input)) return 11;
            std::cout << "Python enum packet passed native pure validation; no dispatch.\n";
            return 0;
        }
        RetainedCallPacket packet{};
        packet.call.version=kEnumCallVersion; packet.call.parameter_size=packet.call.allocation_extent=1;
        packet.call.return_offset=65535; packet.call.target={1,1,0x10000}; packet.call.function={2,1,0x20000};
        packet.call.field_count=1;
        auto& p=packet.call.fields[0]; p.kind=kEnumCallKind; p.width=p.dimension=1; p.flags=0x80;
        std::memcpy(p.name,"Mode",5); p.constraint={3,1,0x30000}; packet.call.data[0]=2;
        if(validate_enum_call(packet) || !validate_call_packet(packet.call,true)) return 3;
        for(unsigned variant=0;variant<6;++variant) {
            auto invalid=packet;
            if(variant==0) invalid.call.fields[0].width=4;
            if(variant==1) invalid.call.fields[0].constraint.address=0;
            if(variant==2) invalid.call.fields[0].kind=13;
            if(variant==3) invalid.call.fields[0].bool_encoding=1;
            if(variant==4) invalid.call.data[1]=1;
            if(variant==5) invalid.count=1;
            if(!validate_enum_call(invalid)) return 4;
        }
        Fixture valid;
        if(!valid.check(0) || !valid.check(2) || !valid.check(255) || valid.check(1)) return 1;
        unsigned rejected=0;
        auto reject=[&](auto change) {
            Fixture f; change(f);
            if(f.check()) throw std::runtime_error("Altered enum schema accepted");
            ++rejected;
        };
        reject([](auto& f){ f.m.stop_after=0; });
        reject([](auto& f){ f.m.stop_after=2; });
        reject([](auto& f){ ++f.id.serial; });
        reject([](auto& f){ f.m.objects.erase(f.enumeration); });
        reject([](auto& f){ f.m.words[f.enumeration+8]=0x40000000; });
        reject([](auto& f){ f.m.words[f.enumeration]=0; });
        reject([](auto& f){ f.m.names[f.cls+0x18]="Class"; });
        reject([](auto& f){ f.m.names[f.package+0x18]="/Script/Other"; });
        reject([](auto& f){ f.m.words[f.property]=0; });
        reject([](auto& f){ f.m.names[0x17000]="ByteProperty"; });
        reject([](auto& f){ f.m.words[f.property+0x78]=f.cls; });
        reject([](auto& f){ f.m.words[f.property+0x34]=4; });
        reject([](auto& f){ f.m.words[f.property+0x30]=2; });
        reject([](auto& f){ f.m.words[f.property+0x70]=f.property; });
        reject([](auto& f){ f.m.words[f.child+0x10]=f.property|1; });
        reject([](auto& f){ f.m.names[0x18000]="IntProperty"; });
        reject([](auto& f){ f.m.words[f.child+0x34]=4; });
        reject([](auto& f){ f.m.words[f.child+0x44]=1; });
        reject([](auto& f){ f.m.words[f.child+0x70]=f.enumeration; });
        reject([](auto& f){ f.m.words[f.enumeration+0x48]=4; });
        reject([](auto& f){ f.m.words[f.enumeration+0x48]=0; });
        reject([](auto& f){ f.m.words[f.enumeration+0x4c]=65537; });
        reject([](auto& f){ f.m.words[f.enumeration+0x40]=0; });
        reject([](auto& f){ f.m.words[f.data+24]=256; });
        std::cout << "Byte-enum schema/membership passed; " << rejected << " malformed/context/identity cases rejected; six invalid wire packets and legacy version rejected.\n";
    } catch(const std::exception& error) { std::cerr << error.what() << '\n'; return 2; }
    return 0;
}
