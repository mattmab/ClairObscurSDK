#define NOMINMAX
#include <windows.h>
#include "target_authored_binding_authority.h"
#include <cassert>

struct FakeQuery {
    uint64_t session=7,base=0;
    bool live=true;
    bool context()const{return live;}
    bool same(const CallIdentity& a,const CallIdentity& b)const{return !std::memcmp(&a,&b,sizeof(a));}
    bool valid(const CallIdentity& id)const{return id.address && id.serial>0;}
};
struct FakeLeases {
    uint64_t addresses[3]{};
    bool owns_object(uint64_t session,uint64_t token,uint64_t address)const {
        return session==7 && token>0 && token<=3 && addresses[token-1]==address;
    }
};
struct Owner {bool current=true,released=true;};
bool owned(void* p,uint64_t session,const CallIdentity&,const CallIdentity&,const CallIdentity&) {
    return static_cast<Owner*>(p)->current && session==7;
}
bool released(void* p) {return static_cast<Owner*>(p)->released;}
int main() {
    alignas(16) uint8_t player[64]{},actor[800]{},root[64]{};
    CallIdentity p{1,1,reinterpret_cast<uint64_t>(player)};
    CallIdentity a{2,1,reinterpret_cast<uint64_t>(actor)};
    CallIdentity r{3,1,reinterpret_cast<uint64_t>(root)};
    std::memcpy(player+32,&a.address,8);std::memcpy(actor+720,&p.address,8);std::memcpy(actor+728,&r.address,8);
    FakeQuery query;FakeLeases leases{{p.address,a.address,r.address}};Owner owner;
    e33_authored_binding::PortableInputs inputs{};inputs.root=r;inputs.root_token=3;
    TargetAuthoredBindingAuthorityOps<FakeQuery,FakeLeases> ops(query,leases,inputs,p,a,1,2,&owner,owned,released);
    assert(ops.owned_player(7,p,a,r));assert(ops.outputs_released());
    assert(!ops.owned_player(8,p,a,r));
    auto forged=p;forged.serial++;assert(!ops.owned_player(7,forged,a,r));
    leases.addresses[1]=0;assert(!ops.owned_player(7,p,a,r));leases.addresses[1]=a.address;
    owner.current=false;assert(!ops.owned_player(7,p,a,r));owner.current=true;
    owner.released=false;assert(!ops.outputs_released());owner.released=true;
    uint64_t stale=0;std::memcpy(actor+728,&stale,8);assert(!ops.owned_player(7,p,a,r));
    std::memcpy(actor+728,&r.address,8);query.live=false;assert(!ops.owned_player(7,p,a,r));
}
