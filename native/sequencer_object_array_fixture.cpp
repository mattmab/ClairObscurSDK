#include "sequencer_object_array.h"
#include <cassert>
#include <stdexcept>
using namespace e33_sequencer_array;
struct Ops {
    bool valid=true,capacity=true,corrupt=false,fail_retain=false,fail_capture=false,throw_dispatch=false,throw_free=false;
    bool freed=false;int dispatched=0;Array header{0x100000,3,4};uint32_t captured=0,retained=0;
    bool validate(){return valid;}
    bool preflight(uint32_t count){assert(count==1 || count==128);return capacity;}
    void dispatch(void* args){++dispatched;if(throw_dispatch)throw std::runtime_error("dispatch");std::memcpy(static_cast<uint8_t*>(args)+(mode==1?8:0),&header,16);if(corrupt)static_cast<uint8_t*>(args)[23]=1;}
    uint32_t mode=1;
    bool read_pointer(uint64_t at,uint64_t& out){out=0x200000+(at-header.data)*0x100;return true;}
    bool capture(uint64_t object,CallIdentity& out){++captured;out={int32_t(captured),0,object};return !fail_capture;}
    bool retain(CallIdentity& id,uint64_t& token){assert(!freed);++retained;token=retained;id.serial=100;return !fail_retain;}
    void free_array(uint64_t address){assert(address==header.data);if(throw_free)throw std::runtime_error("free");freed=true;}
};
static Packet packet(uint32_t mode=1,uint32_t index=0){Packet p{};p.version=3;p.op=220;p.request=1;p.mode=mode;p.index=index;p.target={1,1,0x10000};p.function={2,1,0x20000};p.subject={3,1,0x30000};p.subject_token=1;if(mode==2)p.target=p.subject;return p;}
int main(){
    {Frame f;Ops o;auto p=packet();assert(f.query(o,p)==Result::ok);assert(o.freed && f.count()==3 && f.total()==3);assert(f.outputs()[0].identity.serial==100);assert(f.reset() && f.available());}
    {Frame f;Ops o;o.mode=2;o.header.count=5000;o.header.capacity=6000;auto p=packet(2,4999);assert(f.query(o,p)==Result::ok);assert(o.captured==1 && o.retained==1 && f.total()==5000 && o.freed);}
    {Frame f;Ops o;o.mode=2;auto p=packet(2,3);assert(f.query(o,p)==Result::range && o.freed && !o.retained && f.count()==0);assert(f.reset());}
    {Frame f;Ops o;o.header.count=129;o.header.capacity=256;assert(f.query(o,packet())==Result::range && o.freed && !o.retained);}
    {Frame f;Ops o;o.header={};assert(f.query(o,packet())==Result::ok && !o.freed && !f.count());}
    for(int n=0;n<5;++n){Frame f;Ops o;if(n==0)o.valid=false;if(n==1)o.capacity=false;auto p=packet();if(n==2)p.outputs[0].token=1;if(n==3)p.tail[100]=1;if(n==4)p.function.serial=0;assert(f.query(o,p)==Result::rejected && !o.dispatched && f.available());}
    for(int n=0;n<6;++n){Frame f;Ops o;if(n==0)o.header.count=-1;if(n==1)o.header.capacity=2;if(n==2)o.header.data=1;if(n==3)o.fail_capture=true;if(n==4)o.fail_retain=true;if(n==5){o.mode=2;o.corrupt=true;}assert(f.query(o,packet(o.mode))==Result::unknown);assert(!o.freed && f.quarantined() && !f.reset());}
    for(int n=0;n<2;++n){Frame f;Ops o;o.throw_dispatch=n==0;o.throw_free=n==1;try{f.query(o,packet());assert(false);}catch(const std::runtime_error&){}assert(f.quarantined() && !f.reset());}
    return 0;
}
