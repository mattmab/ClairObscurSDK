#include "authored_curve_patch.h"
#include <cassert>
#include <array>
using namespace e33_curve_patch;
struct ChannelSchema {
    uint64_t parent=0x20000,super=0,fields=0;uint32_t size=80;bool registered=true,expected_name=true;
    template<class T> T read(uint64_t at)const{
        if(at==0x10000+64)return static_cast<T>(parent);
        if(at==0x20000+88)return static_cast<T>(size);
        if(at==0x20000+64)return static_cast<T>(super);
        if(at==0x20000+80)return static_cast<T>(fields);
        return 0;
    }
    bool struct_type(uint64_t at)const{return registered&&at==0x20000;}
    bool named(uint64_t at,const char* name,const char* package)const{
        return expected_name&&at==0x20000&&!std::strcmp(name,"MovieSceneChannel")&&!std::strcmp(package,"/Script/MovieScene");
    }
};
struct Fake {
    int32_t source_times[3]{10,20,30},target_times[3]{10,20,30};
    uint8_t source_values[96]{},target_values[96]{};
    Storage storage{};unsigned writes=0,resolves=0,fail_write=0;bool admitted=true,change_after=false;
    explicit Fake(uint32_t kind){
        storage={reinterpret_cast<uint64_t>(source_times),reinterpret_cast<uint64_t>(source_values),reinterpret_cast<uint64_t>(target_times),reinterpret_cast<uint64_t>(target_values),3,kind};
        std::memset(source_values,0x55,sizeof(source_values));
        for(unsigned i=0;i<3;++i){uint64_t bits=1;if(kind==Float){float value=1;std::memcpy(&bits,&value,4);}if(kind==Double){double value=1;std::memcpy(&bits,&value,8);}std::memcpy(source_values+i*stride(kind),&bits,width(kind));}
        std::memcpy(target_values,source_values,sizeof(source_values));
    }
    bool resolve(const Packet&,Storage& out){++resolves;out=storage;return admitted&&!(change_after&&writes);}
    bool read(uint64_t at,void* out,size_t n){std::memcpy(out,reinterpret_cast<void*>(at),n);return true;}
    bool equal(uint64_t at,const void* expected,size_t n){return !std::memcmp(reinterpret_cast<void*>(at),expected,n);}
    bool write(uint64_t at,const void* value,size_t n){++writes;if(writes==fail_write)return false;std::memcpy(reinterpret_cast<void*>(at),value,n);return true;}
};
Packet packet(uint32_t kind){
    Packet p{};p.request=9;p.source={1,2,0x10000};p.target={2,3,0x20000};p.sequence={3,4,0x30000};p.outer={4,5,0x40000};
    for(unsigned i=0;i<4;++i)p.tokens[i]=i+1;
    p.signature[0]=1;p.kind=kind;p.depth=1;p.key_count=3;p.edit_count=1;
    std::memcpy(p.path[0].field,"FloatCurve",11);p.path[0].element=UINT32_MAX;
    p.edits[0].index=1;p.edits[0].before_time=20;p.edits[0].after_time=21;p.edits[0].before=1;p.edits[0].after=0;
    if(kind==Float){float value=1;std::memcpy(&p.edits[0].before,&value,4);value=.5f;std::memcpy(&p.edits[0].after,&value,4);}
    if(kind==Double){double value=1;std::memcpy(&p.edits[0].before,&value,8);value=.5;std::memcpy(&p.edits[0].after,&value,8);}
    return p;
}
int main(){
    {ChannelSchema schema;assert(channel_base(schema,0x10000));
     schema.parent=0;assert(!channel_base(schema,0x10000));schema.parent=0x20000;
     schema.registered=false;assert(!channel_base(schema,0x10000));schema.registered=true;
     schema.expected_name=false;assert(!channel_base(schema,0x10000));schema.expected_name=true;
     schema.size=88;assert(!channel_base(schema,0x10000));schema.size=80;
     schema.super=0x30000;assert(!channel_base(schema,0x10000));schema.super=0;
     schema.fields=0x40000;assert(!channel_base(schema,0x10000));}
    for(uint32_t kind=Boolean;kind<=Double;++kind){
        Fake ops(kind);auto p=packet(kind);Frame frame;
        const std::array<int32_t,3> original={10,20,30};uint8_t values[96]{};std::memcpy(values,ops.source_values,96);
        assert(request(p)&&frame.patch(ops,p)==Result::Applied);
        assert(ops.writes==2&&!frame.quarantined()&&ops.target_times[1]==21);
        assert(!std::memcmp(ops.source_times,original.data(),12)&&!std::memcmp(ops.source_values,values,96));
        std::memcpy(values+stride(kind),&p.edits[0].after,width(kind));
        assert(!std::memcmp(ops.target_values,values,96)); // Tangents, modes and all other keys unchanged.
        assert(frame.reset());
    }
    {Fake ops(Float);auto p=packet(Float);p.edits[0].after_time=30;Frame frame;assert(frame.patch(ops,p)==Result::Rejected&&ops.writes==0);}
    {Fake ops(Float);auto p=packet(Float);p.edits[0].before=0;Frame frame;assert(frame.patch(ops,p)==Result::Rejected&&ops.writes==0);}
    {Fake ops(Float);auto p=packet(Float);ops.target_values[27]^=1;Frame frame;assert(frame.patch(ops,p)==Result::Rejected&&ops.writes==0);}
    {Fake ops(Float);auto p=packet(Float);ops.storage.target_values=ops.storage.source_values;Frame frame;assert(frame.patch(ops,p)==Result::Rejected&&ops.writes==0);}
    {Fake ops(Float);auto p=packet(Float);ops.admitted=false;Frame frame;assert(frame.patch(ops,p)==Result::Rejected&&ops.writes==0);}
    {Fake ops(Float);auto p=packet(Float);p.edits[0].after=0x7fc00000;Frame frame;assert(frame.patch(ops,p)==Result::Rejected&&ops.writes==0);}
    {Fake ops(Float);auto p=packet(Float);p.edit_count=2;p.edits[1]=p.edits[0];Frame frame;assert(frame.patch(ops,p)==Result::Rejected&&ops.writes==0);}
    {Fake ops(Float);auto p=packet(Float);p.path[1].field[0]='x';Frame frame;assert(frame.patch(ops,p)==Result::Rejected&&ops.writes==0);}
    {Fake ops(Float);auto p=packet(Float);ops.fail_write=2;Frame frame;assert(frame.patch(ops,p)==Result::Unknown&&ops.writes==2);assert(frame.quarantined()&&frame.protects(1)&&frame.protects(4)&&!frame.reset());assert(frame.patch(ops,p)==Result::Rejected&&ops.writes==2);}
    {Fake ops(Double);auto p=packet(Double);ops.change_after=true;Frame frame;assert(frame.patch(ops,p)==Result::Unknown&&frame.quarantined()&&frame.protects(2));}
    {auto p=packet(Boolean);p.edits[0].after=2;assert(!request(p));}
    {auto p=packet(Byte);p.edits[0].after=256;assert(!request(p));}
    {auto p=packet(Integer);p.edits[0].after=0xffffffff;assert(request(p));p.edits[0].after=0x1ffffffffULL;assert(!request(p));}
}
