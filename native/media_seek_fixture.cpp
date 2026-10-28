#include <initializer_list>
#include "invocation_protocol.h"
#include <cstdio>
int main(){
 CallPacket p{};p.version=2;p.parameter_size=9;p.allocation_extent=16;p.return_offset=8;
 p.target={1,1,0x1000};p.function={2,1,0x2000};p.function_flags=79823875;p.entry_rva=0x320ad80;p.field_count=2;
 p.fields[0]={CallTimespan,0,8,1,6755468294751106ULL,0,"Time",{3,1,0x3000}};
 p.fields[1]={CallBool,8,1,1,6755469234276224ULL,0xff010001,"ReturnValue",{-1,0,0}};
#ifdef E33_MEDIA_SEEK_SESSION
 if(validate_call_packet(p,true))return 1;
 auto good=p;
 for(int64_t ticks:{-1LL,864000000001LL}){p=good;std::memcpy(p.data,&ticks,8);if(!validate_call_packet(p,true))return 2;}
 for(uint32_t rva:{0u,0x3208990u,0x3207a70u}){p=good;p.entry_rva=rva;if(!validate_call_packet(p,true))return 3;}
 p=good;p.function_flags++;if(!validate_call_packet(p,true))return 4;
 p=good;p.fields[0].flags=0x80;if(!validate_call_packet(p,true))return 5;
 p=good;p.fields[1].bool_encoding=0x01010001;if(!validate_call_packet(p,true))return 6;
 p=good;p.fields[1].offset=0;if(!validate_call_packet(p,true))return 7;
 p=good;p.parameter_size=16;if(!validate_call_packet(p,true))return 8;
 p=good;int64_t end=864000000000LL;std::memcpy(p.data,&end,8);if(validate_call_packet(p,true))return 9;
#else
 if(!validate_call_packet(p,true))return 10;
#endif
 std::puts("Media Seek packet fixture passed");return 0;
}

