#pragma once
#include <algorithm>
#include <cmath>

namespace e33_editor_flight {
struct TickGate {
    double next=0.;
    bool due(double now){if(now<next)return false;next=now+1./120.;return true;}
};
struct Input {double dx=0,dy=0,forward=0,side=0,up=0;bool fast=false;};
inline bool moving(const Input& i){return i.dx || i.dy || i.forward || i.side || i.up;}
// Shared by the Scene Editor's custom scene and imported sequence viewports.
inline void advance(double (&pose)[6],double dt,const Input& i){
    constexpr double rad=3.141592653589793/180.;
    pose[4]=std::remainder(pose[4]+std::clamp(i.dx,-4096.,4096.)*1.25,360.);
    pose[3]=std::clamp(pose[3]+std::clamp(i.dy,-4096.,4096.)*1.25,-89.,89.);pose[5]=0.;
    const double cp=std::cos(pose[3]*rad),sp=std::sin(pose[3]*rad),cy=std::cos(pose[4]*rad),sy=std::sin(pose[4]*rad);
    const double speed=std::clamp(dt,0.,.05)*1600.*(i.fast?4.:1.)/std::max(1.,std::sqrt(i.forward*i.forward+i.side*i.side+i.up*i.up));
    pose[0]+=speed*(cp*cy*i.forward-sy*i.side);pose[1]+=speed*(cp*sy*i.forward+cy*i.side);pose[2]+=speed*(sp*i.forward+i.up);
    for(unsigned axis=0;axis<3;++axis)pose[axis]=std::clamp(pose[axis],-1.e8,1.e8);
}
}
