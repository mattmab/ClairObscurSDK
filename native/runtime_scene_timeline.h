#pragma once
#include "runtime_scene_plan.h"
namespace e33_runtime_scene {
// Scene-owned timeline hit testing and dragging. No pointer or event ID crosses the wire.
struct TimelineDrag {
    int kind=-1,index=-1,camera_selected=-1,selected_kind=-1,selected_index=-1;
    bool down=false;
    double offset=0.;
    void cancel(){kind=index=-1;down=true;}
    void select_camera(const Plan& p,double seconds){
        camera_selected=-1;for(unsigned i=0;i<unsigned(p.key_count);++i)if(std::abs(p.keys[i][0]-seconds)<.00001)camera_selected=int(i);
    }
    double* value(Plan& p){
        if(kind==1 && index>=0 && index<int(p.count))return p.animation+index;
        if(kind==1 && index>=6 && index<6+int(p.extra_count))return &p.extra[index-6][1];
        if(kind==2 && index>=0 && index<32)return p.audio+index;
        if(kind==3 && index>=0 && index<int(p.key_count))return &p.keys[index][0];
        return nullptr;
    }
    bool sample(Plan& p,unsigned selected,bool pressed,double x,double y,double width,double& seek){
        if(!pressed){kind=index=-1;down=false;return false;}
        const double seconds=(x-.08)/.84*p.duration;
        if(!down){
            down=true;kind=index=-1;
            if(x<.08 || x>.92 || y<.855 || y>.94)return false;
            kind=0;offset=0.;const int lane=y<.885?1:y<.91?2:3;
            double closest=12.*p.duration/(std::max(width,1.)*.84);
            auto hit=[&](double at,int candidate){if(at<0.)return;const double distance=std::abs(seconds-at);if(distance<=closest){closest=distance;kind=lane;index=candidate;}};
            if(lane==1 && selected<unsigned(p.count))hit(p.animation[selected],int(selected));
            if(lane==1)for(int i=0;i<int(p.extra_count);++i)if(p.extra[i][0]==double(selected))hit(p.extra[i][1],6+i);
            if(lane==2)for(int i=0;i<32;++i)hit(p.audio[i],i);
            if(lane==3)for(int i=0;i<int(p.key_count);++i)hit(p.keys[i][0],i);
            if(auto* at=value(p))offset=seconds-*at;
            if(kind>0){selected_kind=kind;selected_index=index;}
            if(kind==3)camera_selected=index;
        }
        if(kind<0)return false;
        if(kind==0){seek=std::clamp(std::round(seconds*30.)/30.,0.,p.duration);return true;}
        auto* at=value(p);if(!at)return false;
        double low=0.,high=kind==3?p.duration:std::floor((p.duration-.001)*30.)/30.;
        if(kind==3){if(index>0)low=p.keys[index-1][0]+1./30.;if(index+1<int(p.key_count))high=p.keys[index+1][0]-1./30.;}
        if(low>high){seek=*at;return true;}
        *at=std::clamp(std::round((seconds-offset)*30.)/30.,low,high);seek=*at;return true;
    }
};
}
