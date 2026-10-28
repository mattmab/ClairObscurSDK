#include "enum_call_protocol.h"
#include "blueprint_call_protocol.h"
#include <cassert>
#include <limits>
#include <initializer_list>

static CallPacket packet(uint32_t kind,uint32_t width,bool output=false) {
    CallPacket p{};p.version=2;p.parameter_size=p.allocation_extent=width;
    p.return_offset=output ? 0 : 65535;p.target={1,1,0x10000};p.function={2,1,0x20000};p.field_count=1;
    auto& f=p.fields[0];f.kind=kind;f.width=width;f.dimension=1;f.flags=output ? 0x580 : 0x80;
    const auto name=output ? "ReturnValue" : "Frame";std::memcpy(f.name,name,std::strlen(name)+1);f.constraint={3,1,0x30000};return p;
}
int main() {
    auto number=packet(CallFrameNumber,4);int32_t negative=-2147483647;std::memcpy(number.data,&negative,4);
    auto time=packet(CallFrameTime,8,true);auto rate=packet(CallFrameRate,8);
    const int32_t good_rate[]={24000,1001};std::memcpy(rate.data,good_rate,8);
#ifdef E33_SEQUENCER_VALUE_SESSION
    assert(!validate_call_packet(number,true));assert(!validate_call_packet(time,true));assert(!validate_call_packet(rate,true));
    rate.data[4]=0;rate.data[5]=rate.data[6]=rate.data[7]=0;assert(validate_call_packet(rate,true));
    std::memcpy(rate.data,good_rate,8);rate.fields[0].dimension=2;assert(validate_call_packet(rate,true));
    time.fields[0].flags=0x80;time.return_offset=65535;float sub=.5f;std::memcpy(time.data+4,&sub,4);
    assert(!validate_call_packet(time,true));
    for(float bad:{-0.1f,1.f,std::numeric_limits<float>::infinity()}) {
        std::memcpy(time.data+4,&bad,4);assert(validate_call_packet(time,true));
    }
    number.version=8;assert(validate_blueprint_call(number));
    auto frame=packet(CallFrameNumber,4);auto retained=RetainedCallPacket{};retained.call=frame;
    retained.call.version=4;retained.call.parameter_size=retained.call.allocation_extent=5;
    retained.call.field_count=2;auto& e=retained.call.fields[1];e.kind=kEnumCallKind;e.offset=4;e.width=e.dimension=1;
    e.flags=0x80;e.constraint={4,1,0x40000};std::memcpy(e.name,"TimeUnit",sizeof("TimeUnit"));
    assert(!validate_enum_call(retained));
#else
    assert(validate_call_packet(number,true));assert(validate_call_packet(time,true));assert(validate_call_packet(rate,true));
#endif
    assert(sequencer_frame_value(CallFrameRate,reinterpret_cast<const uint8_t*>(good_rate),true));
    return 0;
}
