#include "cinematic_component_frame.h"
#include <array>
#include <cstring>
#include <cassert>
#include <iostream>
int main() {
    using namespace e33_cinematic;
    std::array<uint8_t,4096> memory{};
    constexpr uint64_t low=0x10000,frame=low+128,locals=low+1024,result=low+2048,record=low+2304,destination=low+2560;
    auto write=[&](uint64_t at,uint64_t value){std::memcpy(memory.data()+at-low,&value,8);};
    auto read=[&](uint64_t at,void* out,size_t size){
        if(at<low || at-low>memory.size() || size>memory.size()-(at-low)) return false;
        std::memcpy(out,memory.data()+at-low,size);return true;};
    ComponentLookupSite site{0x1000,0x2000,0x3000,0x4000,0x5000,low,low+memory.size(),0x7000};
    write(frame+0x10,site.getter);write(frame+0x90,site.native_function);
    write(frame+0x18,site.library);write(frame+0x20,site.script+75);
    write(frame+0x28,locals);write(locals,0x6000);write(locals+16,site.actor);
    write(frame+0x80,record);write(record,site.return_property);write(record+8,destination);
    ComponentLookupFrame out{};
    assert(component_lookup_frame(read,frame,result,site,out));assert(out.track==0x6000);
    assert(!component_lookup_frame(read,frame,locals+24,site,out));
    assert(!component_lookup_frame(read,frame,frame+0x28,site,out));
    assert(!component_lookup_frame(read,frame,result+1,site,out));
    assert(!component_lookup_frame(read,frame,site.stack_high-4,site,out));
    for(auto offset:{0x10,0x90,0x18,0x20,0x28}) {
        uint64_t saved{};read(frame+offset,&saved,8);write(frame+offset,0);
        assert(!component_lookup_frame(read,frame,result,site,out));write(frame+offset,saved);
    }
    write(frame+0x80,1);assert(!component_lookup_frame(read,frame,result,site,out));write(frame+0x80,record);
    write(locals+16,0x9999);assert(!component_lookup_frame(read,frame,result,site,out));write(locals+16,site.actor);
    write(frame+0x20,site.script+85);
    assert(!component_lookup_frame(read,frame,result,site,out));
    assert(component_lookup_frame(read,frame,result,site,out,true));
    // Every result-bearing identity must come from a distinct locals area.
    // A bounded but aliased locals pointer must fail before its contents matter.
    for(auto alias:{frame,frame+0x18,frame+0xa0,frame-16}) {
        write(frame+0x28,alias);
        assert(!component_lookup_frame(read,frame,result,site,out,true));
        assert(out.track==0);
    }
    write(frame+0x28,locals);
    assert(component_lookup_frame(read,frame,result,site,out,true));
    // Exact single record only: malformed pointers never reach the reader.
    for(auto bad:{uint64_t(0),record+1,frame,locals,result,site.stack_high-16}) {
        write(frame+0x80,bad);assert(!component_lookup_frame(read,frame,result,site,out,true));
        assert(out.track==0);
    }
    write(frame+0x80,record);
    write(record,site.return_property+8);assert(!component_lookup_frame(read,frame,result,site,out,true));
    write(record,site.return_property);
    write(record+16,record);assert(!component_lookup_frame(read,frame,result,site,out,true));write(record+16,0);
    for(auto bad:{uint64_t(0),destination+1,frame,locals+8,result,record,site.stack_high-4}) {
        write(record+8,bad);assert(!component_lookup_frame(read,frame,result,site,out,true));
    }
    write(record+8,destination);
    assert(component_lookup_frame(read,frame,result,site,out,true));
    const auto saved_property=site.return_property;site.return_property=0;
    assert(!component_lookup_frame(read,frame,result,site,out,true));site.return_property=saved_property;
    for(auto rejected:{record,record+8,record+16}) {
        auto unreadable=[&](uint64_t at,void* output,size_t size){return at!=rejected && read(at,output,size);};
        assert(!component_lookup_frame(unreadable,frame,result,site,out,true));
    }
    auto failed=[](uint64_t,void*,size_t){return false;};
    assert(!component_lookup_frame(failed,frame,result,site,out,true));
    assert(out.track==0);
    site.script=UINT64_MAX;assert(!component_lookup_frame(read,frame,result,site,out,true));
    std::cout<<"Cinematic component call-frame checks passed\n";
}
