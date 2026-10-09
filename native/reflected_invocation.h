#pragma once
#include "invocation_protocol.h"
#include <cmath>

// Uses the target's own dispatcher. No thunk ABI emulation, nontrivial native
// values, cached callable addresses or promise that an RPC body ran. The optional
// retention sink owns object outputs before this game-thread operation returns.
inline uint64_t call_identity(uint64_t base, const CallIdentity& id) {
    auto value=fixed_slot(base,id.index,id.serial);
    return value && value==id.address ? value : 0;
}
inline bool call_derives(uint64_t base,uint64_t cls,uint64_t expected) {
    for(unsigned ancestry_depth=0;cls && ancestry_depth<128;++ancestry_depth) {
        auto index=local_read<int32_t>(cls+0xc);
        // Validate registration without assuming classes have nonzero serials.
        int32_t count=local_read<int32_t>(base+0x9361b84);
        if(index<0 || index>=count) return false;
        auto chunks=local_read<uint64_t>(base+0x9361b70);
        auto slot=local_read<uint64_t>(chunks+uint64_t(index>>16)*8)+uint64_t(index&65535)*24;
        if(local_read<uint64_t>(slot)!=cls) return false;
        if(cls==expected) return true;
        cls=local_read<uint64_t>(cls+0x40);
    }
    return false;
}
inline CallIdentity call_capture(uint64_t base,uint64_t object) {
    if(!object) return {-1,0,0};
    auto index=local_read<int32_t>(object+0xc);
    auto count=local_read<int32_t>(base+0x9361b84);
    if(index<0 || index>=count) return {-1,0,0};
    auto chunks=local_read<uint64_t>(base+0x9361b70);
    auto slot=local_read<uint64_t>(chunks+uint64_t(index>>16)*8)+uint64_t(index&65535)*24;
    if(local_read<uint64_t>(slot)!=object) return {-1,0,0};
    return {index,local_read<int32_t>(slot+0x10),object};
}
inline bool call_is_class(uint64_t base,uint64_t object) {
    auto type=local_read<uint64_t>(object+0x10);
    for(unsigned step=0;type && step<128;++step) {
        if(!call_capture(base,type).address) return false;
        if(exact_name(base,type+0x18,"Class")) return true;
        type=local_read<uint64_t>(type+0x40);
    }
    return false;
}
struct CallRetention {
    void* context;
    uint32_t (*preflight)(void*,const CallPacket&);
    uint32_t (*capture)(void*,uint32_t,const CallIdentity&);
};
inline uint32_t reflected_call(uint64_t base,CallPacket& packet,const CallRetention* retention=nullptr) {
    if(auto invalid=validate_call_packet(packet)) return invalid;
    packet.outcome=CallNotDispatched;
    if(packet.version!=kCallVersion || packet.parameter_size>kCallBytes ||
       packet.parameter_size>packet.allocation_extent || packet.allocation_extent>65536 ||
       packet.field_count>kCallFields || packet.object_count>kCallObjects) return 200;
    if(local_read<DWORD>(base+0x9272d30)!=GetCurrentThreadId() ||
       local_read<uint8_t>(base+0x9272cfc) || local_read<uint8_t>(base+0x934e968)) return 201;
    auto object=call_identity(base,packet.target), function=call_identity(base,packet.function);
    if(!object || !function || (local_read<uint32_t>(object+8)&0x40000000)) return 202;
    auto fn_class=local_read<uint64_t>(function+0x10);
    auto owner=local_read<uint64_t>(function+0x20);
    if(!exact_name(base,fn_class+0x18,"Function") ||
       !call_derives(base,local_read<uint64_t>(object+0x10),owner)) return 203;
    if(local_read<uint32_t>(function+0xb0)!=packet.function_flags ||
       local_read<uint16_t>(function+0xb6)!=packet.parameter_size ||
       local_read<uint16_t>(function+0xb8)!=packet.return_offset ||
       local_read<int32_t>(function+0x58)!=static_cast<int32_t>(packet.allocation_extent) ||
       packet.entry_rva>=166776832 || local_read<uint64_t>(function+0xd8)!=base+packet.entry_rva) return 204;
    // First transport supports native functions. Blueprint frames, latent paths
    // and native value construction are separate implementation gates.
    if(!(packet.function_flags&0x400)) return 205;
    auto dispatch=local_read<uint64_t>(local_read<uint64_t>(object)+0x268);
    if(dispatch!=base+0x1393330 && dispatch!=base+0x332bb90) return 206;
    alignas(16) uint8_t arguments[kCallBytes]{};
    uint8_t used[kCallBytes]{};
    std::memcpy(arguments,packet.data,packet.parameter_size);
    auto property=local_read<uint64_t>(function+0x50);
    unsigned seen=0, walked=0, returns=0;
    const char* kinds[]={"", "BoolProperty","ByteProperty","UInt16Property","IntProperty",
                         "FloatProperty","DoubleProperty","ObjectProperty","ClassProperty"};
    for(;property;property=local_read<uint64_t>(property+0x18)) {
        if(++walked>4096) return 207;
        auto flags=local_read<uint64_t>(property+0x38);
        if(!(flags&0x80)) continue;
        if(seen>=packet.field_count) return 208;
        const auto& field=packet.fields[seen++];
        if(field.kind<CallBool || field.kind>CallClass || !field.name[0] || field.name[95] ||
           field.flags!=flags || local_read<uint64_t>(property+0x10)!=(function|1) ||
           !exact_name(base,property+0x20,field.name) ||
           !exact_name(base,local_read<uint64_t>(property+8),kinds[field.kind]) ||
           field.offset!=local_read<uint32_t>(property+0x44) || field.width!=local_read<uint32_t>(property+0x34) ||
           field.dimension!=local_read<uint32_t>(property+0x30) || !field.dimension || field.dimension>64 ||
           !field.width || uint64_t(field.offset)+uint64_t(field.width)*field.dimension>packet.parameter_size) return 209;
        if(flags&0x400) { ++returns; if(field.offset!=packet.return_offset || field.dimension!=1) return 210; }
        unsigned width=field.kind==CallByte ? 1 : field.kind==CallUInt16 ? 2 :
            field.kind==CallInt32 || field.kind==CallFloat ? 4 : 8;
        uint8_t mask=255, byte_offset=0;
        if(field.kind==CallBool) {
            auto encoding=local_read<uint32_t>(property+0x70);
            mask=uint8_t(encoding>>24); byte_offset=uint8_t(encoding>>8);
            auto byte_mask=uint8_t(encoding>>16);
            if(encoding!=field.bool_encoding || !mask || !byte_mask || (byte_mask&~mask) ||
               (byte_mask&(byte_mask-1)) || uint8_t(encoding)!=field.width || byte_offset>=field.width) return 211;
            width=field.width;
        }
        if(field.width!=width) return 212;
        for(unsigned element=0;element<field.dimension;++element) {
            auto at=field.offset+element*width;
            for(unsigned byte=0;byte<width;++byte) {
                uint8_t bits=field.kind==CallBool ? (byte==byte_offset ? mask : 0) : 255;
                if(used[at+byte]&bits) return 213;
                used[at+byte]|=bits;
            }
            if(field.kind==CallFloat && !std::isfinite(local_read<float>(reinterpret_cast<uint64_t>(arguments+at)))) return 214;
            if(field.kind==CallDouble && !std::isfinite(local_read<double>(reinterpret_cast<uint64_t>(arguments+at)))) return 214;
            if(field.kind==CallObject || field.kind==CallClass) {
                if(local_read<uint64_t>(reinterpret_cast<uint64_t>(arguments+at))) return 215;
                auto constraint=call_identity(base,field.constraint);
                if(!constraint || !call_is_class(base,constraint) || local_read<uint64_t>(property+(field.kind==CallClass ? 0x78 : 0x70))!=constraint) return 216;
                unsigned matches=0;
                for(unsigned j=0;j<packet.object_count;++j) if(packet.objects[j].offset==at) {
                    if(++matches>1 || (flags&0x400) || ((flags&0x100) && !(flags&0x8000000))) return 217;
                    auto argument=call_identity(base,packet.objects[j].identity);
                    if(!argument || (field.kind==CallClass && !call_is_class(base,argument)) ||
                       !call_derives(base,field.kind==CallClass ? argument : local_read<uint64_t>(argument+0x10),constraint)) return 218;
                    std::memcpy(arguments+at,&argument,8);
                }
            }
        }
    }
    if(seen!=packet.field_count || returns>1 || ((packet.return_offset==65535)!=(returns==0))) return 219;
    for(unsigned j=0;j<packet.object_count;++j) {
        bool matched=false;
        for(unsigned f=0;f<packet.field_count;++f) {
            const auto& field=packet.fields[f];
            if(field.kind!=CallObject && field.kind!=CallClass) continue;
            for(unsigned i=0;i<field.dimension;++i) if(packet.objects[j].offset==field.offset+i*8) matched=true;
        }
        if(!matched) return 220;
    }
    if(retention) {
        auto error=retention->preflight(retention->context,packet);
        if(error) return error;
    }
    packet.outcome=CallOutcomeUnknown; // A fault/timeout after this point cannot be retried safely.
    using Dispatch=void(__fastcall*)(void*,void*,void*);
    reinterpret_cast<Dispatch>(dispatch)(reinterpret_cast<void*>(object),reinterpret_cast<void*>(function),arguments);
    // Capture and scrub all pointer slots, including input references. Never
    // publish raw pointer bytes as return values. Only the explicit retention
    // sink acquires ownership; the established v6/v7 path remains observational.
    packet.object_count=0;
    for(unsigned f=0;f<packet.field_count;++f) {
        const auto& field=packet.fields[f];
        if(field.kind!=CallObject && field.kind!=CallClass) continue;
        for(unsigned i=0;i<field.dimension;++i) {
            auto offset=field.offset+i*8;
            auto value=local_read<uint64_t>(reinterpret_cast<uint64_t>(arguments+offset));
            if(value) {
                if(packet.object_count>=kCallObjects) return 221;
                auto identity=call_capture(base,value);
                if(!identity.address) return 222;
                auto constraint=call_identity(base,field.constraint);
                if(!constraint || (field.kind==CallClass && !call_is_class(base,value)) ||
                   !call_derives(base,field.kind==CallClass ? value : local_read<uint64_t>(value+0x10),constraint)) return 224;
                packet.objects[packet.object_count++]={offset,identity};
                if(retention && (field.flags&0x500)) {
                    auto error=retention->capture(retention->context,offset,identity);
                    if(error) return error; // Session still owns every acquired holder.
                }
            }
            std::memset(arguments+offset,0,8);
        }
    }
    if(!call_identity(base,packet.target) || !call_identity(base,packet.function)) return 223;
    std::memcpy(packet.data,arguments,packet.parameter_size);
    packet.outcome=CallDispatchReturned;
    return 0;
}
