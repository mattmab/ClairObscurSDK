#include "sequence_seek_protocol.h"
#include <cassert>
#include <limits>
int main() {
    SequenceSeekPacket p{};p.magic=0x53533345;p.version=1;
    p.function={0,1,0x10000};p.frame=-24;p.subframe=0.5f;
    assert(sequence_seek_request(p));assert(sequence_seek_range(p,-30,60));
    auto bad=p;bad.subframe=std::numeric_limits<float>::quiet_NaN();assert(!sequence_seek_request(bad));
    bad=p;bad.subframe=std::numeric_limits<float>::infinity();assert(!sequence_seek_request(bad));
    bad=p;bad.subframe=-0.1f;assert(!sequence_seek_request(bad));
    bad=p;bad.subframe=1;assert(!sequence_seek_request(bad));
    bad=p;bad.outcome=1;assert(!sequence_seek_request(bad));
    for(unsigned i=0;i<7;++i) {bad=p;bad.reserved[i]=1;assert(!sequence_seek_request(bad));}
    bad=p;bad.function.serial=0;assert(!sequence_seek_request(bad));
    bad=p;bad.frame=-31;assert(!sequence_seek_range(bad,-30,60));
    bad=p;bad.frame=30;assert(!sequence_seek_range(bad,-30,60));
    bad.subframe=0;assert(sequence_seek_range(bad,-30,60));
    bad.frame=31;assert(!sequence_seek_range(bad,-30,60));
    assert(!sequence_seek_range(p,INT32_MAX-1,10));
    assert(!sequence_seek_range(p,-30,0));assert(!sequence_seek_range(p,-30,-1));
    uint8_t bytes[56];std::memset(bytes,0xff,sizeof(bytes));sequence_seek_parameters(p,bytes);
    int32_t frame=0;float subframe=0;std::memcpy(&frame,bytes,4);std::memcpy(&subframe,bytes+4,4);
    assert(frame==-24 && subframe==0.5f);
    for(unsigned i=8;i<52;++i) assert(bytes[i]==0);
    assert(bytes[52]==0 && bytes[53]==2 && bytes[54]==1 && bytes[55]==0);
}
