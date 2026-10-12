#include "sequence_camera_journal.h"
#include "sequence_camera_protocol.h"
#include <cassert>
#include <stdexcept>
#include <iostream>
using e33_camera::Result;
struct Ops {
    int current_value=2,capture_count=0,restore_count=0,release_count=0;
    bool live=true,proof=true,retain=true,throw_restore=false;
    Result capture_result=Result::ok,read_result=Result::ok,restore_result=Result::ok,release_result=Result::ok;
    bool context(){return live;}
    bool same(int a,int b){return a==b;}
    Result capture(int&,int& original){++capture_count;original=2;return capture_result;}
    Result current(int,int& out){out=current_value;return read_result;}
    bool proven_owned(int camera){return proof && camera==3;}
    bool retain_owned(int){return retain;}
    Result restore(int,int){++restore_count;if(throw_restore)throw std::runtime_error("dispatch fault");return restore_result;}
    Result release(){++release_count;return release_result;}
};
int main(){
    CallPacket c{}; c.version=1;c.parameter_size=21;c.allocation_extent=24;c.return_offset=65535;
    c.function_flags=67240962;c.entry_rva=0x3b2c940;c.field_count=5;c.target={1,1001,0x1000};c.function={2,1002,0x2000};
    const char* names[]={"NewViewTarget","BlendTime","blendFunc","BlendExp","bLockOutgoing"};
    uint32_t kinds[]={CallObject,CallFloat,CallByte,CallFloat,CallBool},offsets[]={0,8,12,16,20},widths[]={8,4,1,4,1};
    for(unsigned i=0;i<5;++i){auto& f=c.fields[i];strcpy_s(f.name,names[i]);f.kind=kinds[i];f.offset=offsets[i];f.width=widths[i];f.dimension=1;
        f.flags=i?6755469234274944ULL:6755468160533120ULL;f.bool_encoding=i==4?0xff010001:0;}
    c.fields[0].constraint={3,1003,0x3000};assert(camera_restore_packet(c));
    auto reject=[&](auto change){auto bad=c;change(bad);assert(!camera_restore_packet(bad));};
    reject([](auto& p){p.data[8]=1;});reject([](auto& p){p.data[12]=1;});reject([](auto& p){p.data[20]=1;});
    reject([](auto& p){p.entry_rva++;});reject([](auto& p){p.function_flags++;});reject([](auto& p){p.parameter_size=24;});
    reject([](auto& p){p.fields[0].constraint.address=0;});reject([](auto& p){p.fields[2].flags=0x80;});
    reject([](auto& p){p.object_count=1;p.objects[0]={0,{5,1005,0x5000}};});reject([](auto& p){p.fields[4].bool_encoding=0;});

    {Ops o;e33_camera::Journal<int> j;assert(j.arm(o,1)==Result::ok);assert(j.close(o)==Result::ok);assert(o.restore_count==0&&o.release_count==1);}
    {Ops o;e33_camera::Journal<int> j;assert(j.arm(o,1)==Result::ok);assert(j.created());assert(j.close(o)==Result::ok);assert(o.restore_count==0);}
    {Ops o;e33_camera::Journal<int> j;j.arm(o,1);j.created();assert(j.admit_owned(o,3)==Result::ok);o.current_value=3;
     assert(j.close(o)==Result::ok);assert(o.restore_count==1&&o.release_count==1);assert(j.close(o)==Result::ok);assert(o.restore_count==1);}
    {Ops o;e33_camera::Journal<int> j;j.arm(o,1);j.created();o.current_value=4;assert(j.close(o)==Result::unknown);assert(j.quarantined());assert(o.restore_count==0&&o.release_count==0);}
    {Ops o;e33_camera::Journal<int> j;j.arm(o,1);j.created();o.proof=false;assert(j.admit_owned(o,3)==Result::rejected);o.current_value=3;assert(j.close(o)==Result::unknown);}
    {Ops o;e33_camera::Journal<int> j;j.arm(o,1);j.created();j.admit_owned(o,3);o.current_value=3;o.restore_result=Result::deferred;
     assert(j.close(o)==Result::deferred);o.restore_result=Result::ok;assert(j.close(o)==Result::ok);assert(o.restore_count==2);}
    {Ops o;e33_camera::Journal<int> j;j.arm(o,1);j.created();j.admit_owned(o,3);o.current_value=3;o.restore_result=Result::unknown;
     assert(j.close(o)==Result::unknown);assert(j.close(o)==Result::unknown);assert(o.restore_count==1&&o.release_count==0);}
    {Ops o;e33_camera::Journal<int> j;j.arm(o,1);j.created();j.admit_owned(o,3);o.current_value=3;o.throw_restore=true;
     try{j.close(o);assert(false);}catch(const std::runtime_error&){} assert(j.close(o)==Result::unknown);assert(o.restore_count==1);}
    {Ops o;e33_camera::Journal<int> j;j.arm(o,1);j.created();o.read_result=Result::rejected;assert(j.close(o)==Result::unknown);assert(o.restore_count==0);}
    {Ops o;e33_camera::Journal<int> j;j.arm(o,1);j.created();o.release_result=Result::deferred;assert(j.close(o)==Result::deferred);
     o.release_result=Result::ok;assert(j.close(o)==Result::ok);assert(o.restore_count==0&&o.release_count==2);}
    {Ops o;e33_camera::Journal<int> j;o.capture_result=Result::rejected;assert(j.arm(o,1)==Result::rejected);assert(!j.active());}
    {Ops o;e33_camera::Journal<int> j;o.capture_result=Result::unknown;assert(j.arm(o,1)==Result::unknown);assert(j.quarantined());}
    {Ops o;e33_camera::Journal<int> j;j.arm(o,1);j.created();o.live=false;assert(j.close(o)==Result::deferred);assert(o.release_count==0);}
    std::cout<<"13 bounded camera journal scenarios and 10 altered restore packets passed\n";
}

