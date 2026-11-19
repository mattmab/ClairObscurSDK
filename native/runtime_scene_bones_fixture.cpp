#include "runtime_scene_bones.h"
#include <cstdio>
#include <limits>
int main(){
    using e33_runtime_scene::BoneTimeline;
    BoneTimeline t;uint32_t indices[]={1};
    if(!t.configure(1,1,2,1.,5.,30.,indices))return 1;
    float a[]={0,0,0,1,0,0,10,1,1,1},b[]={0,0,1,0,0,0,30,1,1,1};
    if(!t.append(0,1,a)||t.active(2.)||t.append(0,1,a))return 2;
    b[0]=std::numeric_limits<float>::quiet_NaN();if(t.append(1,1,b))return 3;b[0]=0;
    if(!t.append(1,1,b)||!t.active(0.)||t.active(5.))return 4;
    float p[10]{};t.sample(1.+1./60,0,p);
    if(std::abs(p[6]-20)>1.e-3 || std::abs(p[2]-.70710678)>1.e-4 || std::abs(p[3]-.70710678)>1.e-4)return 5;
    t.sample(0.,0,p);if(p[6]!=10)return 6;
    t.sample(4.,0,p);if(p[6]!=30)return 7;
    t.reset();if(t.active(0.)||!t.values.empty())return 8;
    std::puts("Bone timeline upload, malformed pose rejection, interpolation, holds, and cleanup passed.");
}
