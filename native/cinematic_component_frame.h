#pragma once
#include <cstdint>
#include <cstddef>

namespace e33_cinematic {
// Exact GetCinematicsSystem -> Actor.GetComponentByClass callsite, build 23765773.
// Caller must verify script bytes/reflection, retained UObject identities and GT.
// This helper reads only a bounded native stack frame and does not write memory.
struct ComponentLookupSite {
    uint64_t getter{}, native_function{}, script{}, library{}, actor{};
    uint64_t stack_low{}, stack_high{}, return_property{};
};
struct ComponentLookupFrame {
    uint64_t locals{}, track{}, actor{}, result{};
};
inline bool stack_region(uint64_t address, size_t size, const ComponentLookupSite& site) {
    return site.stack_low && site.stack_low < site.stack_high && address >= site.stack_low &&
        address <= site.stack_high && size <= site.stack_high-address;
}
inline bool overlaps(uint64_t a, size_t as, uint64_t b, size_t bs) {
    return a < b+bs && b < a+as; // Only called after bounded stack-region checks.
}
template<class Reader>
bool component_lookup_frame(Reader&& read, uint64_t frame, uint64_t result,
                            const ComponentLookupSite& site, ComponentLookupFrame& out,
                            bool after_original = false) {
    out={};
    if (!site.getter || !site.native_function || !site.script || !site.library || !site.actor || !site.return_property ||
        site.script > UINT64_MAX-115 || !stack_region(frame,0xa8,site) ||
        !stack_region(result,8,site) || (result&7) || overlaps(frame,0xa8,result,8)) return false;
    uint64_t getter{}, native{}, context{}, code{}, locals{}, track{}, actor{}, out_chain{};
    auto field=[&](uint64_t offset, uint64_t& value) { return read(frame+offset,&value,8); };
    if (!field(0x10,getter) || !field(0x90,native) || !field(0x18,context) ||
        !field(0x20,code) || !field(0x28,locals) || !field(0x80,out_chain) ||
        getter!=site.getter || native!=site.native_function || context!=site.library ||
        code!=site.script+(after_original ? 85 : 75) ||
        !stack_region(locals,32,site) || overlaps(locals,32,frame,0xa8) || overlaps(locals,32,result,8) ||
        !read(locals,&track,8) || !read(locals+16,&actor,8) || !track || actor!=site.actor) return false;
    // The exact Blueprint getter has one return property and no out parameters.
    // Its FFrame therefore owns one FOutParmRec, even at the nested native call.
    // PropAddr is the OUTER caller's return destination, not this hook result.
    if((out_chain&7) || !stack_region(out_chain,24,site) ||
       overlaps(out_chain,24,frame,0xa8) || overlaps(out_chain,24,locals,32) ||
       overlaps(out_chain,24,result,8)) return false;
    uint64_t property{},destination{},next{};
    if(!read(out_chain,&property,8) || !read(out_chain+8,&destination,8) ||
       !read(out_chain+16,&next,8) || property!=site.return_property || next ||
       (destination&7) || !stack_region(destination,8,site) ||
       overlaps(destination,8,frame,0xa8) || overlaps(destination,8,locals,32) ||
       overlaps(destination,8,out_chain,24) || overlaps(destination,8,result,8)) return false;
    out={locals,track,actor,result};
    return true;
}
}
