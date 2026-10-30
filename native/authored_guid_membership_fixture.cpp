#define NOMINMAX
#include <windows.h>
#include "target_authored_binding_query.h"
#include "authored_guid_membership.h"
#include <cassert>
#include <cstring>
using e33_camera_binding::ObjectArray;
struct Reader {
    alignas(8) uint8_t spawn[480]{},possess[256]{};
    ObjectArray headers[2]{};
    bool stable=true,mutate_header=false,mutate_other=false;
    unsigned header_calls=0;
    Reader(){headers[0]={reinterpret_cast<uint64_t>(spawn),2,2};headers[1]={reinterpret_cast<uint64_t>(possess),2,2};}
    void set(unsigned kind,unsigned row,const uint32_t (&guid)[4]) {
        auto* base=kind?possess:spawn;std::memcpy(base+row*(kind?128:240)+(kind?56:160),guid,16);
    }
    uint32_t word(uint64_t address)const{uint32_t v{};std::memcpy(&v,reinterpret_cast<void*>(address),4);return v;}
    ObjectArray header(unsigned kind) {
        if(mutate_other && header_calls++==0){const uint32_t replacement[]{1,2,3,4};set(0,1,replacement);}
        auto h=headers[kind];if(mutate_header)++h.count;return h;
    }
    bool context()const{return stable;}
};
int main(){
    const uint32_t target[]{1,2,3,4},other[]{5,6,7,8};
    Reader r;r.set(1,0,target);r.set(0,0,other);
    assert(e33_authored_guid::unique_stable(r,r.headers,target));
    r.set(0,1,target);assert(!e33_authored_guid::unique_stable(r,r.headers,target));
    r.set(0,1,other);r.mutate_other=true;assert(!e33_authored_guid::unique_stable(r,r.headers,target));
    r.mutate_other=false;r.set(0,1,other);r.mutate_header=true;
    assert(!e33_authored_guid::unique_stable(r,r.headers,target));
    r.mutate_header=false;r.stable=false;assert(!e33_authored_guid::unique_stable(r,r.headers,target));
    r.stable=true;r.headers[0].count=513;assert(!e33_authored_guid::unique_stable(r,r.headers,target));
    r.headers[0].count=-1;assert(!e33_authored_guid::unique_stable(r,r.headers,target));
}
