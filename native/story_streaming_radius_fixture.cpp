#include "story_streaming_radius.h"
#include <cassert>
#include <limits>
#include <initializer_list>
using namespace e33_story_streaming;
template<class T> void put(Shape& shape,size_t offset,T value){std::memcpy(shape.bytes+offset,&value,sizeof(value));}
struct Ops {
    Shape shape{};unsigned reads=0,writes=0;bool valid=true,write_ok=true,change_other=false,change_storage=false;
    Ops(){put(shape,4,1.f);put(shape,8,50000.f);put(shape,16,360.f);}
    bool observe(uint64_t& address,Shape& observed){++reads;address=0x10000+(change_storage&&writes?8:0);observed=shape;return valid;}
    bool write(uint64_t,float radius){++writes;if(!write_ok)return false;put(shape,8,radius);if(change_other)put(shape,16,90.f);return true;}
};
int main(){
    Packet p{};p.owner=1;p.actor={1,2,0x10000};p.component={3,4,0x20000};p.radius=8000;
    assert(valid(p));p.tail[0]=1;assert(!valid(p));p.tail[0]=0;p.component.serial=0;assert(!valid(p));p.component.serial=4;
    for(float radius:{0.f,999.f,50001.f,std::numeric_limits<float>::infinity(),std::numeric_limits<float>::quiet_NaN()}){
        p.radius=radius;assert(!valid(p));Ops ops;Journal journal;assert(configure(journal,radius,ops)==rejected&&!journal.attempted&&!ops.writes);
    }
    for(float radius:{1000.f,8000.f,50000.f}){
        Ops ops;Journal journal;const auto before=ops.shape;
        assert(!configure(journal,radius,ops)&&journal.acknowledged&&ops.writes==1&&at<float>(ops.shape,8)==radius);
        for(size_t i=0;i<72;++i)if(i<8||i>=12)assert(before.bytes[i]==ops.shape.bytes[i]);
        assert(configure(journal,radius,ops)==rejected&&ops.writes==1);
    }
    {Ops ops;Journal journal;ops.valid=false;assert(configure(journal,8000,ops)==rejected&&!journal.attempted&&!ops.writes);}
    for(size_t offset:{size_t(0),size_t(4),size_t(8),size_t(12),size_t(16),size_t(24),size_t(64)}){
        Ops ops;Journal journal;ops.shape.bytes[offset]^=1;
        assert(configure(journal,8000,ops)==rejected&&!journal.attempted&&!ops.writes);
    }
    for(unsigned mode=0;mode<3;++mode){
        Ops ops;Journal journal;ops.write_ok=mode!=0;ops.change_other=mode==1;ops.change_storage=mode==2;
        assert(configure(journal,8000,ops)==uncertain&&journal.attempted&&!journal.acknowledged);
        assert(configure(journal,8000,ops)==rejected&&ops.writes==1);
    }
}
