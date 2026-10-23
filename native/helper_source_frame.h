#pragma once
#include <cmath>
#include <cstdint>
#include <cstring>
namespace e33_enemy_spawn {
inline bool unit_yaw_frame(const double* pose,double bound){
    double norm=0;
    for(unsigned i=0;i<12;++i)if(i!=7&&i!=11&&(!std::isfinite(pose[i])||std::abs(pose[i])>bound))return false;
    for(unsigned i=0;i<4;++i)norm+=pose[i]*pose[i];
    return std::abs(norm-1)<1.e-6&&std::abs(pose[0])<1.e-6&&std::abs(pose[1])<1.e-6&&
        std::abs(pose[8]-1)<1.e-6&&std::abs(pose[9]-1)<1.e-6&&std::abs(pose[10]-1)<1.e-6;
}
// Preserve the ordinary frame limit. The sole larger admitted source frame
// is the measured original Paintress helper relative to its initial arena.
// Class authority is checked by the owning native caller, not supplied on wire.
inline bool helper_relative_frame(const double* relative,bool paintress_source=false){
    if(unit_yaw_frame(relative,100000.))return true;
    if(!paintress_source||!unit_yaw_frame(relative,125000.))return false;
    constexpr double position[]={118904.97848443517,24590.077704791423,-91119.19637107503};
    const double half_yaw=90.66391375564693*3.14159265358979323846/360.;
    const double dot=relative[2]*std::sin(half_yaw)+relative[3]*std::cos(half_yaw);
    if(std::abs(std::abs(dot)-1)>1.e-6)return false;
    for(unsigned i=0;i<3;++i)if(std::abs(relative[4+i]-position[i])>.1)return false;
    return true;
}
inline bool compose_helper_source_frame(const double* arena,const double* relative,double* result,bool paintress_source=false){
    if(!unit_yaw_frame(arena,1.e7)||!helper_relative_frame(relative,paintress_source))return false;
    const double cosine=arena[3]*arena[3]-arena[2]*arena[2],sine=2*arena[3]*arena[2];
    const double pose[]={0,0,arena[2]*relative[3]+arena[3]*relative[2],arena[3]*relative[3]-arena[2]*relative[2],
        arena[4]+cosine*relative[4]-sine*relative[5],arena[5]+sine*relative[4]+cosine*relative[5],arena[6]+relative[6],0,1,1,1,0};
    if(!unit_yaw_frame(pose,1.e7))return false;std::memcpy(result,pose,sizeof(pose));return true;
}
inline bool same_helper_world_frame(const double* observed,const double* expected){
    if(!unit_yaw_frame(observed,1.e7)||!unit_yaw_frame(expected,1.e7))return false;
    double dot=0;for(unsigned i=0;i<4;++i)dot+=observed[i]*expected[i];
    if(std::abs(std::abs(dot)-1)>1.e-6)return false;
    for(unsigned i=4;i<7;++i)if(std::abs(observed[i]-expected[i])>.1)return false;
    return true;
}
struct HelperSourceFrameReport {
    double arena[12]{},helper[12]{},expected[12]{};
    uint32_t attempted=0,tick_acknowledged=0,visibility_acknowledged=0,verified=0;
};
static_assert(sizeof(HelperSourceFrameReport)==304,"helper source frame copied report");
}
