#include "portable_binding_frame.h"
#include <cassert>
using namespace e33_portable_binding;
Packet packet(){
    Packet p{};p.version=3;p.operation=operation;p.request=1;
    p.target={1,1,0x10000};p.function={2,1,0x20000};p.root={3,1,0x30000};p.destination=p.root;p.source={4,1,0x40000};
    for(unsigned i=0;i<5;++i)p.tokens[i]=i+1;p.guid[0]=42;return p;
}
struct Ops {
    int calls=0,validations=0;bool valid=true,changed_context=false,changed_input=false,bad_guid=false,empty=false,throws=false;
    bool validate(){++validations;return valid&&!(changed_context&&validations>1);}
    void dispatch(void* raw){
        ++calls;if(throws)throw 1;auto* b=static_cast<uint8_t*>(raw);
        if(!empty)std::memcpy(b+40,b+16,16);
        if(changed_input)b[0]^=1;if(bad_guid)b[40]^=1;
    }
};
int main(){
    auto p=packet();assert(request(p));
    const unsigned offsets[]={24U,168U,192U,196U,20983U};
    for(unsigned at:offsets){
        auto bad=p;reinterpret_cast<uint8_t*>(&bad)[at]=1;assert(!request(bad));
    }
    {Frame f;Ops o;o.valid=false;assert(f.query(o,p)==Result::Rejected);assert(o.calls==0&&f.available());}
    {Frame f;Ops o;assert(f.query(o,p)==Result::Complete);assert(o.calls==1&&f.result());
     assert(!std::memcmp(f.result(),p.guid,16));assert(f.query(o,p)==Result::Rejected);f.reset();assert(f.available());}
    {Frame f;Ops o;o.empty=true;assert(f.query(o,p)==Result::Unavailable);assert(f.result());f.reset();assert(f.available());}
    for(unsigned mode=0;mode<4;++mode){Frame f;Ops o;o.changed_context=mode==0;o.changed_input=mode==1;o.bad_guid=mode==2;o.throws=mode==3;
        try{assert(f.query(o,p)==Result::Unknown);}catch(int){assert(mode==3);}
        assert(f.quarantined());f.reset();assert(!f.available());assert(f.query(o,p)==Result::Rejected);assert(o.calls==1);
    }
}
