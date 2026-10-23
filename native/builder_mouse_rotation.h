#pragma once
#include <cmath>
namespace e33_builder {
// Uniform multiplicative scaling preserves proportions and mirrored axes.
inline double mouse_uniform_scale(double* scale,double delta) {
    double smallest=1.e300,largest=0.;
    for(int i=0;i<3;++i){const double v=std::abs(scale[i]);if(!std::isfinite(v)||v==0.)return 1.;smallest=std::fmin(smallest,v);largest=std::fmax(largest,v);}
    double factor=std::exp(std::fmax(-1.,std::fmin(1.,delta*.02)));
    if(factor>1.)factor=std::fmax(1.,std::fmin(factor,1000./largest));
    else factor=std::fmin(1.,std::fmax(factor,.001/smallest));
    for(int i=0;i<3;++i)scale[i]*=factor;
    return factor;
}
// World-axis delta composed with the existing quaternion; translation/scale
// are deliberately outside this helper. Unreal pitch/roll use negative Y/X.
inline void mouse_axis_quaternion(double* q,int axis,double degrees) {
    const double half=degrees*3.14159265358979323846/360.;
    double d[3]{};d[axis==1?2:axis==2?1:0]=std::sin(half)*(axis==1?1.:-1.);
    const double w=std::cos(half),x=q[0],y=q[1],z=q[2],s=q[3];
    q[0]=w*x+d[0]*s+d[1]*z-d[2]*y;
    q[1]=w*y-d[0]*z+d[1]*s+d[2]*x;
    q[2]=w*z+d[0]*y-d[1]*x+d[2]*s;
    q[3]=w*s-d[0]*x-d[1]*y-d[2]*z;
    const double n=std::sqrt(q[0]*q[0]+q[1]*q[1]+q[2]*q[2]+q[3]*q[3]);
    for(int i=0;i<4;++i)q[i]/=n;
}
struct MouseRotationGesture {
    int axis=0;bool changed=false;double angle=0.;
    void reset(){axis=0;changed=false;angle=0.;}
    void select(int wanted){if(wanted!=axis){reset();axis=wanted;if(axis==4)angle=1.;}}
};
}
