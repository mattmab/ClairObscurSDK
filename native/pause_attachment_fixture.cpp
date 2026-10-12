#include <cstdint>
#include <cstddef>
#include <cstring>
#include <cmath>
#include <cstdio>
#include <vector>
#include "pause_attachment_protocol.h"
static std::vector<uint64_t> dispatched;
static uint32_t failure=0;
template<class T> T local_read(uint64_t at) {
    if(at==0x1010) return static_cast<T>(0x5000);
    if(at==0x2010) return static_cast<T>(0x6000);
    if(at==0x120 || at==0x220 || at==0x320) return static_cast<T>(0x7000);
    return T{};
}
static uint64_t call_identity(uint64_t,const CallIdentity& id) { return id.address; }
static bool exact_name(uint64_t,uint64_t at,const char* name) {
    return (at==0x118 && !std::strcmp(name,"RemoveFromParent")) ||
        (at==0x218 && !std::strcmp(name,"SetRenderOpacity")) ||
        (at==0x318 && !std::strcmp(name,"SetIsEnabled")) ||
        (at==0x5018 && !std::strcmp(name,"WBP_BaseButton_C")) ||
        (at==0x6018 && !std::strcmp(name,"Overlay")) ||
        (at==0x7018 && !std::strcmp(name,"Widget"));
}
static uint32_t reflected_call(uint64_t,CallPacket& c,const void* =nullptr,
    const void* =nullptr,const void* =nullptr,const void* =nullptr,bool preflight=false) {
    if(preflight) return 0;
    dispatched.push_back(c.function.address);
    if(failure==201) { c.outcome=CallNotDispatched; return 201; }
    c.outcome=CallDispatchReturned;return failure;
}
#include "pause_attachment.h"
struct Pool { bool owns_object(uint64_t,uint64_t lease,uint64_t obj) { return (lease==11 && obj==0x1000)||(lease==12 && obj==0x2000); } };
static CallPacket plan(unsigned kind) {
    CallPacket c{};c.version=1;c.return_offset=65535;
    c.target={1,1,kind ? 0x2000ull:0x1000ull};c.function={2,1,0x100ull*(kind+1)};
    if(kind) {
        c.field_count=1;auto& f=c.fields[0];f.kind=kind==1?CallFloat:CallBool;
        f.dimension=1;f.width=kind==1?4:1;f.flags=0x80;
        strcpy_s(f.name,kind==1?"InOpacity":"bInIsEnabled");
        f.bool_encoding=kind==1?0:0xff010001;
        c.parameter_size=c.allocation_extent=f.width;
        if(kind==1) { float v=1.;std::memcpy(c.data,&v,4); } else c.data[0]=1;
    }
    return c;
}
static uint32_t send(PauseAttachment& owner,unsigned op,uint64_t lease=0,const CallPacket* c=nullptr) {
    PauseAttachmentPacket p{};p.version=1;p.operation=op;p.owner=99;p.lease=lease;
    if(c) p.remove=*c;Pool pool;owner.command(0,7,pool,p);return p.error;
}
int main() {
    auto remove=plan(0),opacity=plan(1),enabled=plan(2);
    auto hide=opacity,disable=enabled;std::memset(hide.data,0,sizeof(hide.data));std::memset(disable.data,0,sizeof(disable.data));
    PauseAttachment owner;
    if(send(owner,1,11,&remove)||send(owner,3,12,&opacity)||send(owner,4,12,&enabled)) return 1;
    if(!owner.protects(11)||!owner.protects(12)||send(owner,5,0,&hide)||send(owner,6,0,&disable)) return 2;
    dispatched.clear();if(owner.close(0,false)) return 3;
    if(dispatched!=std::vector<uint64_t>{0x300,0x200,0x100} || owner.protects(11)||owner.protects(12)) return 4;
    if(send(owner,1,11,&remove)) return 5;
    failure=201;if(owner.close(0,false)!=407 || !owner.protects(11)) return 6;
    failure=0;if(owner.close(0,false)) return 7;
    if(send(owner,1,11,&remove)||send(owner,3,12,&opacity)||send(owner,5,0,&hide)) return 8;
    failure=9;dispatched.clear();if(owner.close(0,false)!=1303) return 9;
    auto count=dispatched.size();if(owner.close(0,false)!=1303 || dispatched.size()!=count || !owner.protects(12)) return 10;
    if(owner.close(0,true)||owner.protects(12)) return 11;
    failure=0;
    PauseAttachmentPool owners; Pool leases;
    for(uint64_t id=1;id<=5;++id) {
        PauseAttachmentPacket p{};p.version=1;p.operation=1;p.owner=id;p.lease=11;p.remove=remove;
        owners.command(0,7,leases,p);
        if((id<=4 && p.error) || (id==5 && p.error!=1301)) return 12;
    }
    PauseAttachmentPacket bad{};bad.version=1;bad.operation=2;bad.owner=77;
    owners.command(0,7,leases,bad);if(bad.error!=1301) return 13;
    dispatched.clear();if(owners.close(0,false) || dispatched.size()!=4 || owners.protects(11)) return 14;
    std::puts("Pause attachment: restore-before-detach, bounded multiple owners, deferred GC and no replay passed");
}
