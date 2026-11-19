#pragma once
#include <vector>
#include <array>
#include <cmath>
#include <algorithm>
#include <cstring>

namespace e33_runtime_scene {
// One bounded authored performance per scene. Static corrective bones are
// uploaded once and skipped thereafter; interpolated primary joints run locally.
struct BoneTimeline {
    static constexpr unsigned max_bones=384,max_frames=96;
    unsigned slot=0,bones=0,frames=0,received=0;
    double hold=0,end=0,fps=30;
    std::vector<uint32_t> indices;
    std::vector<float> values,last;
    std::vector<uint8_t> uploaded;
    bool configured=false,ticking=false,has_last=false;
    bool active(double seconds)const{return configured && received==frames && seconds>=0 && seconds<end;}
    bool configure(unsigned actor,unsigned bone_count,unsigned frame_count,double h,double e,double rate,const uint32_t* ids) {
        if(configured || actor>=6 || !bone_count || bone_count>max_bones || !frame_count || frame_count>max_frames ||
           !std::isfinite(h)||!std::isfinite(e)||!std::isfinite(rate)||h<0||e<=h||e>120||rate<1||rate>60)return false;
        for(unsigned i=0;i<bone_count;++i){if(ids[i]>=8192)return false;for(unsigned j=0;j<i;++j)if(ids[j]==ids[i])return false;}
        slot=actor;bones=bone_count;frames=frame_count;hold=h;end=e;fps=rate;
        indices.assign(ids,ids+bones);values.resize(size_t(bones)*frames*10);last.resize(size_t(bones)*10);uploaded.resize(frames);
        configured=true;return true;
    }
    bool append(unsigned frame,unsigned count,const float* data){
        if(!configured || frame>=frames || count!=bones || uploaded[frame])return false;
        for(unsigned b=0;b<bones;++b){const auto p=data+b*10;double n=0;
            for(unsigned j=0;j<10;++j)if(!std::isfinite(p[j])||std::abs(p[j])>1.e6)return false;
            for(unsigned j=0;j<4;++j)n+=double(p[j])*p[j];
            if(std::abs(n-1.)>1.e-4 || p[7]<=0 || p[8]<=0 || p[9]<=0)return false;
        }
        std::copy(data,data+size_t(bones)*10,values.begin()+size_t(frame)*bones*10);uploaded[frame]=1;++received;return true;
    }
    void sample(double seconds,unsigned bone,float* out)const{
        double f=std::clamp((seconds-hold)*fps,0.,double(frames-1));
        const auto a=unsigned(f),b=std::min(a+1,frames-1);const double t=f-a;
        const auto x=values.data()+(size_t(a)*bones+bone)*10,y=values.data()+(size_t(b)*bones+bone)*10;
        double dot=0;for(unsigned i=0;i<4;++i)dot+=double(x[i])*y[i];
        const double sign=dot<0?-1.:1.;dot=std::abs(dot);
        double u=1.-t,v=t;
        if(dot<.9995){const double angle=std::acos(std::clamp(dot,0.,1.)),den=std::sin(angle);u=std::sin((1.-t)*angle)/den;v=std::sin(t*angle)/den;}
        double n=0;for(unsigned i=0;i<4;++i){out[i]=float(u*x[i]+v*sign*y[i]);n+=double(out[i])*out[i];}
        for(unsigned i=0;i<4;++i)out[i]=float(out[i]/std::sqrt(n));
        for(unsigned i=4;i<10;++i)out[i]=float(x[i]+(y[i]-x[i])*t);
    }
    bool changed(unsigned bone,const float* pose)const{
        if(!has_last)return true;
        const auto old=last.data()+bone*10;
        for(unsigned j=0;j<10;++j)if(std::abs(old[j]-pose[j])>1.e-5f)return true;
        return false;
    }
    void reset(){*this=BoneTimeline{};}
};
}
