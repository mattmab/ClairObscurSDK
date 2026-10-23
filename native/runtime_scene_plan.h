#pragma once
#include "runtime_scene_palette.h"
#include <algorithm>
namespace e33_runtime_scene {
struct Plan {
    uint32_t magic=0,version=0;
    double duration=0,count=0,roles[6]{},poses[6][9]{},animation[6]{},clips[6]{},loops[6]{},bindings[3]{},audio[32]{},impact[9]{},recoil[9]{},trail[2]{},camera[7]{},anchor[4]{},editor_camera[6]{},anchor_valid=0,camera_valid=0,key_count=0,keys[16][8]{};
    double extra_count=0,extra[24][4]{},gains[32]{};
    unsigned active_animation(unsigned actor,double seconds)const{
        unsigned result=actor;double latest=animation[actor];
        for(unsigned i=0;i<unsigned(extra_count);++i)if(extra[i][0]==double(actor) && extra[i][1]>=0. && extra[i][1]<=seconds && (latest>seconds || extra[i][1]>=latest)){result=6+i;latest=extra[i][1];}
        return result;
    }
    double start(unsigned event)const{return event<6?animation[event]:extra[event-6][1];}
    double clip(unsigned event)const{return event<6?clips[event]:extra[event-6][2];}
    double loop(unsigned event)const{return event<6?loops[event]:extra[event-6][3];}
    bool camera_pose(double seconds,double* result)const{
        if(!key_count || !std::isfinite(seconds))return false;
        unsigned a=0,b=0;const unsigned n=unsigned(key_count);
        for(unsigned i=1;i<n && seconds>=keys[i][0];++i)a=i;
        b=seconds<=keys[0][0]?0:std::min(a+1,n-1);
        const double t=a==b?0.:std::clamp((seconds-keys[a][0])/(keys[b][0]-keys[a][0]),0.,1.);
        for(unsigned i=0;i<7;++i){const double from=keys[a][i+1],delta=keys[b][i+1]-from;result[i]=from+t*(i>=3 && i<6?std::remainder(delta,360.):delta);}
        return true;
    }
    void camera_world(double seconds,double* result)const{
        double shot[7]{};
        if(!camera_pose(seconds,shot)){shot[0]=-200.;shot[1]=-250.;shot[2]=camera[2];shot[3]=-10.;shot[6]=camera[6];}
        const double rad=anchor[3]*3.141592653589793/180.,c=std::cos(rad),s=std::sin(rad);
        result[0]=anchor[0]+c*shot[0]-s*shot[1];result[1]=anchor[1]+s*shot[0]+c*shot[1];result[2]=anchor[2]+shot[2];
        result[3]=shot[3];result[4]=std::remainder(anchor[3]+shot[4],360.);result[5]=shot[5];result[6]=shot[6];
    }
    int capture_editor_camera(double seconds,double fov){
        const double rad=anchor[3]*3.141592653589793/180.,c=std::cos(rad),s=std::sin(rad);
        const double x=editor_camera[0]-anchor[0],y=editor_camera[1]-anchor[1],z=editor_camera[2]-anchor[2];
        const double pose[]={c*x+s*y,-s*x+c*y,z,editor_camera[3],std::remainder(editor_camera[4]-anchor[3],360.),editor_camera[5],fov};
        for(unsigned i=0;i<7;++i)if(!std::isfinite(pose[i]) || (i<3 && std::abs(pose[i])>5000.) || (i>=3 && i<6 && std::abs(pose[i])>360.))return -1;
        if(fov<20. || fov>120.)return -1;
        const int index=editable_camera_key(seconds);if(index<0)return -1;
        std::copy(pose,pose+7,keys[index]+1);return index;
    }
    int editable_camera_key(double seconds){
        const double at=std::clamp(std::round(seconds*30.)/30.,0.,duration);
        for(unsigned i=0;i<unsigned(key_count);++i)if(std::abs(keys[i][0]-at)<.00001)return int(i);
        if(key_count>=16.)return -1;
        double shot[7]{};
        if(!camera_pose(at,shot)){shot[0]=-200.;shot[1]=-250.;shot[2]=camera[2];shot[3]=-10.;shot[6]=camera[6];}
        unsigned index=0;while(index<unsigned(key_count) && keys[index][0]<at)++index;
        for(unsigned i=unsigned(key_count);i>index;--i)std::copy(keys[i-1],keys[i-1]+8,keys[i]);
        keys[index][0]=at;std::copy(shot,shot+7,keys[index]+1);++key_count;return int(index);
    }
    bool integer(double v,double low,double high)const{return std::isfinite(v) && v>=low && v<=high && std::floor(v)==v;}
    bool valid()const{
        if(magic!=0x314e4353 || version!=6 || !std::isfinite(duration) || duration<2. || duration>120. || !integer(count,0,6))return false;
        for(double gain:gains)if(!std::isfinite(gain) || gain<0. || gain>2.)return false;
        if(!integer(extra_count,0,24))return false;
        for(unsigned i=0;i<24;++i){
            for(double v:extra[i])if(!std::isfinite(v))return false;
            if(i>=unsigned(extra_count)){for(double v:extra[i])if(v!=0.)return false;continue;}
            if(extra[i][1]==-1.){if(extra[i][0]!=0. || extra[i][2]!=-1. || extra[i][3]!=0.)return false;continue;}
            if(!integer(extra[i][0],0,count-1) || extra[i][1]<0. || extra[i][1]>=duration || !integer(extra[i][2],-1,scene_clip_count-1) || !integer(extra[i][3],0,1))return false;
        }
        for(unsigned i=0;i<6;++i)if(!integer(roles[i],0,scene_role_count-1) || !integer(clips[i],-1,scene_clip_count-1) || !integer(loops[i],0,1) || !std::isfinite(animation[i]) || (animation[i]<0. && (animation[i]!=-1. || clips[i]!=-1.)) || animation[i]>=duration)return false;
        if(!integer(anchor_valid,0,1) || !integer(camera_valid,0,1))return false;
        if(!integer(key_count,0,16))return false;
        for(unsigned k=0;k<16;++k){
            for(double v:keys[k])if(!std::isfinite(v))return false;
            if(k>=unsigned(key_count)){for(double v:keys[k])if(v!=0.)return false;continue;}
            if(keys[k][0]<0. || keys[k][0]>duration || (k && keys[k][0]<=keys[k-1][0]))return false;
            for(unsigned i=1;i<7;++i)if(std::abs(keys[k][i])>(i<4?5000.:360.))return false;
            if(keys[k][7]<20. || keys[k][7]>120.)return false;
        }
        for(unsigned i=0;i<4;++i)if(!std::isfinite(anchor[i]) || std::abs(anchor[i])>(i<3?1.e8:360.))return false;
        for(unsigned i=0;i<6;++i)if(!std::isfinite(editor_camera[i]) || std::abs(editor_camera[i])>(i<3?1.e8:360.))return false;
        for(unsigned i=0;i<3;++i)if(!integer(bindings[i],-1,count-1) || (bindings[i]>=0. && roles[unsigned(bindings[i])]!=double(i)))return false;
        for(const auto& pose:poses){
            for(unsigned i=0;i<9;++i)if(!std::isfinite(pose[i]) || (i<3?std::abs(pose[i])>5000.:i<6?std::abs(pose[i])>360.:pose[i]<.001 || pose[i]>3.))return false;
            if(pose[6]!=pose[7] || pose[7]!=pose[8])return false;
        }
        for(auto range:{std::pair<const double*,size_t>{audio,32},{impact,9},{recoil,9},{trail,2}})
            for(size_t i=0;i<range.second;++i)if(!std::isfinite(range.first[i]) || (range.first[i]!=-1. && (range.first[i]<0. || range.first[i]>=duration)))return false;
        for(unsigned i=0;i<9;++i){const unsigned attacker=(i==1 || i==3 || i==6)?1U:0U;
            if((audio[i]>=0. || impact[i]>=0. || recoil[i]>=0.) && (bindings[attacker]<0. || bindings[2]<0.))return false;}
        for(unsigned i=0;i<2;++i)if(trail[i]>=0. && bindings[i]<0.)return false;
        for(double v:camera)if(!std::isfinite(v))return false;
        return camera[0]>=100. && camera[0]<=2000. && std::abs(camera[1])<=5000. && camera[2]>=20. && camera[2]<=2000. && std::abs(camera[3])<=500. && camera[4]>=0. && camera[4]<camera[5] && camera[5]<=duration && camera[6]>=20. && camera[6]<=120.;
    }
};
static_assert(sizeof(Plan)==3304,"scene plan ABI");
}
