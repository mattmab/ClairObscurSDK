#pragma once
#include <cmath>

namespace e33_enemy_ground {
enum class Support { Accepted, Unsupported, Rejected };
inline constexpr double heading_offsets[]={0.,-15.,15.,-30.,30.,-45.,45.,-60.,60.};
// Read-only support probes. Every candidate retains the complete radial player
// separation and stays within the forward 120-degree sector. No actor moves here.
template<class Probe>
Support search(const double* origin,double yaw,double distance,Probe&& probe,double* chosen){
    if(!origin||!chosen||!std::isfinite(origin[0])||!std::isfinite(origin[1])||
       !std::isfinite(yaw)||!std::isfinite(distance)||distance<=0||distance>200000.)return Support::Rejected;
    for(const auto degrees:heading_offsets){
        const auto angle=yaw+degrees*3.14159265358979323846/180.;
        const double point[]={origin[0]+std::cos(angle)*distance,origin[1]+std::sin(angle)*distance};
        const auto result=probe(point);
        if(result==Support::Rejected)return result;
        if(result==Support::Accepted){chosen[0]=point[0];chosen[1]=point[1];return result;}
    }
    return Support::Unsupported;
}
}
