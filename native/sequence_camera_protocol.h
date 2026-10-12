#pragma once
#include "invocation_protocol.h"
// Wire-only preflight, independently fixture tested. Native owner additionally
// verifies exact live function identity/owner/schema/entry through reflected_call.
inline bool camera_restore_packet(const CallPacket& c) {
    if(validate_call_packet(c) || c.version!=1 || c.parameter_size!=21 || c.allocation_extent!=24 ||
       c.return_offset!=65535 || c.function_flags!=67240962 || c.entry_rva!=0x3b2c940 ||
       c.field_count!=5 || c.object_count) return false;
    for(auto byte:c.data) if(byte) return false;
    const char* names[]={"NewViewTarget","BlendTime","blendFunc","BlendExp","bLockOutgoing"};
    const uint32_t kinds[]={CallObject,CallFloat,CallByte,CallFloat,CallBool},offsets[]={0,8,12,16,20},widths[]={8,4,1,4,1};
    for(unsigned i=0;i<5;++i) {
        const auto& f=c.fields[i];
        if(std::strcmp(f.name,names[i]) || f.kind!=kinds[i] || f.offset!=offsets[i] || f.width!=widths[i] ||
           f.dimension!=1 || f.flags!=(i ? 6755469234274944ULL : 6755468160533120ULL) ||
           f.bool_encoding!=(i==4 ? 0xff010001 : 0)) return false;
    }
    return true;
}
