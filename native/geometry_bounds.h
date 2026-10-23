#pragma once
#include <algorithm>
#include <cmath>
namespace e33_geometry {
struct BoundsUnion {
    double low[3]{},high[3]{};unsigned count=0;
    bool add(const double* center,const double* extent){
        if(!center||!extent)return false;
        for(unsigned i=0;i<3;++i)if(!std::isfinite(center[i])||!std::isfinite(extent[i])||
            std::abs(center[i])>1.e7||extent[i]<0||extent[i]>1.e5)return false;
        if(extent[0]==0&&extent[1]==0&&extent[2]==0)return true;
        for(unsigned i=0;i<3;++i){
            const auto a=center[i]-extent[i],b=center[i]+extent[i];
            low[i]=count?std::min(low[i],a):a;high[i]=count?std::max(high[i],b):b;
        }
        ++count;return true;
    }
    bool result(double* center,double* extent)const{
        if(!count||!center||!extent)return false;
        for(unsigned i=0;i<3;++i){center[i]=(low[i]+high[i])*.5;extent[i]=(high[i]-low[i])*.5;}
        return true;
    }
};
}
