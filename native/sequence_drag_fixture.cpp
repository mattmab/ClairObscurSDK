#include "sequence_drag_protocol.h"
#include <cassert>
#include <limits>
#include <initializer_list>
int main(){
    SequenceDragConfig c{};c.start=-158;c.end=5345;int32_t frame{};float sub{};
    assert(sequence_drag_position(c,0,frame,sub) && frame==-158 && sub==0);
    assert(sequence_drag_position(c,1,frame,sub) && frame==5344 && sub==0);
    assert(sequence_drag_position(c,.5f,frame,sub) && frame==2593 && sub==.5f);
    assert(!sequence_drag_position(c,std::numeric_limits<float>::quiet_NaN(),frame,sub));
    assert(!sequence_drag_position(c,-.1f,frame,sub));assert(!sequence_drag_position(c,1.1f,frame,sub));
    c.start=INT32_MIN;c.end=INT32_MAX;
    for(float value:{0.f,.25f,.5f,.999999f,1.f}){
        assert(sequence_drag_position(c,value,frame,sub));assert(frame>=c.start && frame<c.end && sub>=0 && sub<1);
    }
    c.end=c.start;assert(!sequence_drag_position(c,0,frame,sub));
    double left=0,right=100;
    assert(sequence_viewport_zoom(0,100,.25,1,false,left,right));
    assert(std::abs((left+.25*(right-left))-25)<.000001);
    assert(right-left<100 && left>=0 && right<=100);
    assert(sequence_viewport_zoom(0,100,.25,-12,false,left,right) && left==0 && right==100);
    left=25;right=75;
    assert(sequence_viewport_zoom(0,100,.5,12,true,left,right) && left==0 && right==50);
    assert(sequence_viewport_zoom(0,100,.5,-12,true,left,right) && left==50 && right==100);
    left=0;right=100;
    for(int i=0;i<100;++i)assert(sequence_viewport_zoom(0,100,.5,1,false,left,right));
    assert(right-left>=1.);
    assert(!sequence_viewport_zoom(0,100,NAN,1,false,left,right));
    assert(sequence_timeline_lane(.755)==0 && sequence_timeline_lane(.805)==2 && sequence_timeline_lane(.905)==6);
    assert(sequence_timeline_lane(.94)==-1 && sequence_timeline_ruler(.94));
    assert(!sequence_timeline_ruler(.805) && !sequence_timeline_ruler(.5));
}
