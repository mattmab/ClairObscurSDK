#include "volume_query.h"
#include "mesh_profile.h"
#include "volume_query_profile.h"
#include <cstdio>
#include <cstdlib>
#include <limits>
int main(){
    using namespace e33_volume_query;
    unsigned tests=0,calls=0;
    auto check=[&](bool value){++tests;if(!value){std::fprintf(stderr,"volume query check %u failed\n",tests);std::exit(1);}};
    check(box_profile.extent<=464&&box_profile.returned==424&&box_profile.params==425);
    check(box_profile.count==15&&box_fields[9].offset==136&&box_fields[9].width==248);
    double center[]={10,20,30},half[]={40,50,60};uint64_t ignored[]={0x10000,0x20000};
    auto clear=[&](uint8_t* frame){
        ++calls;uint64_t context=0;std::memcpy(&context,frame,8);
        check(context==0x30000&&!std::memcmp(frame+8,center,24)&&!std::memcmp(frame+32,center,24));
        check(!std::memcmp(frame+56,half,24)&&frame[384]==1&&frame[104]==0&&frame[128]==0);
        IgnoredActors observed{};std::memcpy(&observed,frame+112,16);
        check(observed.data==ignored&&observed.num==2&&observed.max==2);
        return true;
    };
    check(sample(clear,0x30000,center,half,ignored,2)==Result::Clear);
    check(calls==1);
    check(sample([](uint8_t* frame){frame[424]=1;return true;},0x30000,center,half,nullptr,0)==Result::Blocked);
    check(sample([](uint8_t*){return false;},0x30000,center,half,nullptr,0)==Result::Rejected);
    check(sample([](uint8_t* frame){frame[424]=2;return true;},0x30000,center,half,nullptr,0)==Result::Invalid);
    auto forbidden=[&](uint8_t*){++calls;return true;};
    check(sample(forbidden,0,center,half,nullptr,0)==Result::Invalid);
    check(sample(forbidden,0x30000,nullptr,half,nullptr,0)==Result::Invalid);
    check(sample(forbidden,0x30000,center,half,nullptr,1)==Result::Invalid);
    check(sample(forbidden,0x30000,center,half,ignored,65)==Result::Invalid);
    half[0]=0;check(sample(forbidden,0x30000,center,half,nullptr,0)==Result::Invalid);half[0]=40;
    center[0]=std::numeric_limits<double>::quiet_NaN();
    check(sample(forbidden,0x30000,center,half,nullptr,0)==Result::Invalid);
    check(calls==1);
    std::printf("%u volume query checks passed\n",tests);return 0;
}
