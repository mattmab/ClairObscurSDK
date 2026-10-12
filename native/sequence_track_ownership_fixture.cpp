#include "sequence_track_ownership.h"
#include <array>
#include <cassert>
#include <cstring>
#include <iostream>

int main() {
    std::array<unsigned char, 0x6000> memory{};
    auto set = [&](size_t offset, auto value) { std::memcpy(memory.data()+offset, &value, sizeof(value)); };
    auto read = [&](uint64_t address, void* value, size_t length) {
        if (address > memory.size() || length > memory.size()-address) return false;
        std::memcpy(value, memory.data()+address, length); return true;
    };
    constexpr uint64_t player=0x100, track=0x800, linker=0x1000, shared=0x1800;
    constexpr uint64_t registry=0x2000, slots=0x3000, inputs=0x5000;
    constexpr uint32_t handle=0x00070002;
    set(player+0x2d8,linker); set(track+0x38,linker); set(player+0x2e0,shared);
    set(shared+0x38,handle); set(track+0x40,inputs);
    set(track+0x48,int32_t{1}); set(track+0x4c,int32_t{1});
    set(linker+0x548,registry); set(registry+8,slots);
    set(registry+0x30,int32_t{3}); set(registry+0x18,uint32_t{4});
    set(slots+2*0x110+0x104,uint16_t{7});
    set(inputs,uint64_t{0x5500}); set(inputs+8,handle);
    e33_cinematic::TrackRootMatch result;
    auto matches=[&] { return e33_cinematic::match_root_track(read,player,track,result); };
    assert(matches() && result.inputs==1 && result.handle==handle);
    set(track+0x48,int32_t{2}); set(track+0x4c,int32_t{2});
    set(inputs+16,uint64_t{0x5520}); set(inputs+24,uint32_t{0x00070003});
    assert(!matches()); // Same asset can belong to an unrelated evaluation.
    set(inputs+24,handle); assert(matches() && result.inputs==2);
    set(track+0x48,int32_t{1}); set(track+0x4c,int32_t{1});
    set(inputs+8,uint32_t{0x00080002}); assert(!matches() && !result.linker); // Reused instance.
    set(inputs+8,handle); set(registry+0x18,uint32_t{0}); assert(!matches()); // Freed slot.
    set(registry+0x18,uint32_t{4}); set(slots+2*0x110+0x104,uint16_t{8}); assert(!matches());
    set(slots+2*0x110+0x104,uint16_t{7}); set(track+0x38,uint64_t{0x1100}); assert(!matches());
    set(track+0x38,linker); set(track+0x48,int32_t{0}); assert(!matches()); // Removal needs retained ownership.
    set(track+0x48,int32_t{17}); assert(!matches());
    set(track+0x48,int32_t{1}); set(registry+0x30,int32_t{129}); assert(!matches()); // Invalid inline bitmap.
    set(registry+0x30,int32_t{3}); set(registry+0x28,uint64_t{0x5800}); set(0x5800,uint32_t{4});
    assert(matches());
    set(track+0x40,UINT64_MAX-4); assert(!matches()); // Address overflow/read boundary.
    set(track+0x40,inputs); set(shared+0x38,uint32_t{0xffff}); assert(!matches());
    assert(!e33_cinematic::match_root_track(read,UINT64_MAX-1,track,result));
    std::cout << "sequence track root ownership fixture passed\n";
}
