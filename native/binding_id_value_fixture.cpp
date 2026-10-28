#include "invocation_protocol.h"
#include "blueprint_call_protocol.h"
#include <cassert>
int main(){
    CallPacket p{};p.version=2;p.parameter_size=p.allocation_extent=24;p.return_offset=65535;
    p.target={1,1,0x10000};p.function={2,1,0x20000};p.field_count=1;
    auto& f=p.fields[0];f.kind=CallBindingID;f.width=24;f.dimension=1;f.flags=0x80;f.constraint={3,1,0x30000};
    std::memcpy(f.name,"Binding",8);std::memset(p.data,0xff,24);
    assert(pod_value_width(PodValueKind::BindingID)==24);
    assert(valid_pod_value(PodValueKind::BindingID,p.data,24));
#ifdef E33_SEQUENCE_BINDING_VALUE_SESSION
    assert(!validate_call_packet(p,true));
    f.dimension=2;p.parameter_size=p.allocation_extent=48;assert(validate_call_packet(p,true));
    f.dimension=1;p.parameter_size=p.allocation_extent=24;
    auto bad=p;bad.fields[0].width=16;assert(validate_call_packet(bad,true));
    bad=p;bad.version=1;assert(validate_call_packet(bad,true));
    bad=p;bad.fields[0].constraint.address=0;assert(validate_call_packet(bad,true));
    bad=p;bad.version=8;bad.function_flags=0;bad.entry_rva=kBlueprintThunkRva;assert(validate_blueprint_call(bad));
#else
    assert(validate_call_packet(p,true));
#endif
}
