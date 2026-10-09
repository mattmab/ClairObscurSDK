#pragma once
#include <cstdint>
#include <cstring>
#include <cmath>

constexpr uint32_t kCallVersion = 1, kCallBytes = 4096, kCallFields = 128, kCallObjects = 128;
enum CallKind : uint32_t { CallBool=1, CallByte, CallUInt16, CallInt32, CallFloat, CallDouble, CallObject, CallClass };
enum CallOutcome : uint32_t { CallNotDispatched=0, CallDispatchReturned=1, CallOutcomeUnknown=2 };
#pragma pack(push, 1)
struct CallIdentity { int32_t index, serial; uint64_t address; };
struct CallField {
    uint32_t kind, offset, width, dimension;
    uint64_t flags;
    uint32_t bool_encoding;
    char name[96];
    CallIdentity constraint;
};
struct CallObjectSlot { uint32_t offset; CallIdentity identity; };
struct CallPacket {
    uint32_t version, parameter_size, allocation_extent, return_offset, function_flags, entry_rva;
    uint32_t field_count, object_count, outcome, error;
    CallIdentity target, function;
    CallField fields[kCallFields];
    CallObjectSlot objects[kCallObjects];
    uint8_t data[kCallBytes];
};
#pragma pack(pop)
static_assert(sizeof(CallIdentity)==16 && sizeof(CallField)==140 && sizeof(CallObjectSlot)==20);
static_assert(sizeof(CallPacket)==24648);

// Pure wire validation: usable in fixtures before reading any game memory.
inline uint32_t validate_call_packet(const CallPacket& p) {
    if(p.version!=kCallVersion || p.parameter_size>kCallBytes || p.parameter_size>p.allocation_extent ||
       p.allocation_extent>65536 || p.field_count>kCallFields || p.object_count>kCallObjects || p.outcome || p.error ||
       p.target.index<0 || !p.target.address || p.function.index<0 || !p.function.address) return 300;
    uint8_t used[kCallBytes]{};
    unsigned returns=0;
    for(unsigned f=0;f<p.field_count;++f) {
        const auto& field=p.fields[f];
        if(field.kind<CallBool || field.kind>CallClass || !field.name[0] || field.name[95] || !(field.flags&0x80) ||
           !field.dimension || field.dimension>64 || !field.width ||
           uint64_t(field.offset)+uint64_t(field.dimension)*field.width>p.parameter_size) return 301;
        for(unsigned i=0;i<96 && field.name[i];++i) if(static_cast<unsigned char>(field.name[i])>=128) return 301;
        for(unsigned prior=0;prior<f;++prior) if(std::strcmp(field.name,p.fields[prior].name)==0) return 301;
        if(field.flags&0x400) { ++returns; if(field.offset!=p.return_offset || field.dimension!=1) return 302; }
        unsigned width=field.kind==CallByte ? 1 : field.kind==CallUInt16 ? 2 :
            field.kind==CallInt32 || field.kind==CallFloat ? 4 : 8;
        uint8_t mask=255, offset=0, byte_mask=0;
        if(field.kind==CallBool) {
            mask=uint8_t(field.bool_encoding>>24); offset=uint8_t(field.bool_encoding>>8);
            byte_mask=uint8_t(field.bool_encoding>>16); width=uint8_t(field.bool_encoding);
            if(!mask || !byte_mask || (byte_mask&~mask) || (byte_mask&(byte_mask-1)) || offset>=width) return 303;
        }
        if(field.width!=width) return 304;
        bool input=!(field.flags&0x400) && (!(field.flags&0x100) || (field.flags&0x8000000));
        for(unsigned element=0;element<field.dimension;++element) {
            auto at=field.offset+element*width;
            for(unsigned byte=0;byte<width;++byte) {
                uint8_t bits=field.kind==CallBool ? (byte==offset ? mask : 0) : 255;
                if(used[at+byte]&bits) return 305;
                used[at+byte]|=bits;
                if(!input && (p.data[at+byte]&bits)) return 306;
            }
            if(field.kind==CallBool && (p.data[at+offset]&mask)!=0 && (p.data[at+offset]&mask)!=byte_mask) return 307;
            if(field.kind==CallFloat) { float n; std::memcpy(&n,p.data+at,4); if(!std::isfinite(n)) return 308; }
            if(field.kind==CallDouble) { double n; std::memcpy(&n,p.data+at,8); if(!std::isfinite(n)) return 308; }
            if(field.kind==CallObject || field.kind==CallClass) {
                uint64_t pointer; std::memcpy(&pointer,p.data+at,8);
                if(pointer || field.constraint.index<0 || !field.constraint.address) return 309;
            }
        }
    }
    if(returns>1 || ((p.return_offset==65535)!=(returns==0))) return 310;
    for(unsigned byte=0;byte<kCallBytes;++byte) if(p.data[byte]&~used[byte]) return 311;
    for(unsigned i=0;i<p.object_count;++i) {
        const auto& object=p.objects[i]; bool found=false;
        if(object.identity.index<0 || !object.identity.address) return 312;
        for(unsigned prior=0;prior<i;++prior) if(p.objects[prior].offset==object.offset) return 312;
        for(unsigned f=0;f<p.field_count;++f) {
            const auto& field=p.fields[f];
            if((field.kind!=CallObject && field.kind!=CallClass) || (field.flags&0x400) ||
               ((field.flags&0x100) && !(field.flags&0x8000000))) continue;
            for(unsigned e=0;e<field.dimension;++e) if(object.offset==field.offset+e*8) found=true;
        }
        if(!found) return 313;
    }
    return 0;
}
