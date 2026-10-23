#pragma once
#include <cmath>
#include <cstdint>
namespace e33_component_pose {
// A helper correction preserves its already observed positive scale. This
// validates the packet; ownership and unchanged-scale checks precede dispatch.
inline bool scaled(const double* pose){
    double norm=0;
    for(unsigned i=0;i<12;++i)if(!std::isfinite(pose[i])||std::abs(pose[i])>100000.)return false;
    for(unsigned i=0;i<4;++i)norm+=pose[i]*pose[i];
    return std::abs(norm-1.)<=1.e-6&&pose[7]==0&&pose[11]==0&&
        pose[8]>0&&pose[9]>0&&pose[10]>0&&pose[8]<=1000&&pose[9]<=1000&&pose[10]<=1000;
}
inline bool preserves_scale(const double* a,const double* b){
    if(!scaled(a)||!scaled(b))return false;
    for(unsigned i=8;i<11;++i)if(std::abs(a[i]-b[i])>1.e-6)return false;
    return true;
}
inline bool same_scaled(const double* a,const double* b){
    if(!preserves_scale(a,b))return false;
    double dot=0;for(unsigned i=0;i<4;++i)dot+=a[i]*b[i];
    if(std::abs(std::abs(dot)-1.)>1.e-6)return false;
    for(unsigned i=4;i<7;++i)if(std::abs(a[i]-b[i])>.001)return false;
    return true;
}
inline bool rigid(const double* pose){
    double norm=0;
    for(unsigned i=0;i<12;++i)if(!std::isfinite(pose[i])||std::abs(pose[i])>100000.)return false;
    for(unsigned i=0;i<4;++i)norm+=pose[i]*pose[i];
    return std::abs(norm-1.)<=1.e-6&&pose[7]==0&&pose[11]==0&&
        std::abs(pose[8]-1.)<=1.e-6&&std::abs(pose[9]-1.)<=1.e-6&&std::abs(pose[10]-1.)<=1.e-6;
}
inline bool same(const double* a,const double* b){
    if(!rigid(a)||!rigid(b))return false;
    double dot=0;for(unsigned i=0;i<4;++i)dot+=a[i]*b[i];
    if(std::abs(std::abs(dot)-1.)>1.e-6)return false;
    for(unsigned i=4;i<7;++i)if(std::abs(a[i]-b[i])>.001)return false;
    return true;
}
struct Report {double before[12]{},after[12]{};uint32_t attempted=0,acknowledged=0,readback=0,verified=0;};
static_assert(sizeof(Report)==208,"component pose copied report");
}
