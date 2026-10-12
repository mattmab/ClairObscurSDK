#include "invocation_protocol.h"
#include <limits>
#include <iostream>
int main() {
    CallPacket p{};
    p.version=kPodCallVersion; p.parameter_size=p.allocation_extent=24;
    p.return_offset=65535; p.target={1,1,0x1000}; p.function={2,1,0x2000};
    p.field_count=1;
    auto& f=p.fields[0]; f.kind=CallVector; f.width=24; f.dimension=1; f.flags=0x80;
    f.constraint={3,1,0x3000}; std::memcpy(f.name,"WorldDirection",15);
    double data[3]={0,0,1}; std::memcpy(p.data,data,24);
    if(validate_call_packet(p,true)) return 1;
    if(!validate_call_packet(p,false)) return 2;
    f.width=16; if(!validate_call_packet(p,true)) return 3; f.width=24;
    data[2]=std::numeric_limits<double>::quiet_NaN(); std::memcpy(p.data,data,24);
    if(!validate_call_packet(p,true)) return 4;
    data[2]=1; std::memcpy(p.data,data,24);
    for(auto kind:{13u,14u,16u}) { f.kind=kind; if(!validate_call_packet(p,true)) return 5; }
    std::cout << "Vector call: valid 24-byte doubles; wrong capability, width, nonfinite and reserved kinds rejected.\n";
}
