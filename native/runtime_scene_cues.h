#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
namespace e33_runtime_scene {
struct BlockingKey {uint32_t actor=0,linear=0;double at=0,pose[9]{};};
struct SceneCues {
 uint32_t magic=0,version=0,count=0,cuts=0;
 BlockingKey keys[32]{};
 double source_offsets[30]{};
 bool valid(double duration,unsigned actors,unsigned cameras)const{
  if(magic!=0x31514353U || (version!=1 && version!=2) || count>32 || actors>6 || cameras>16 || (cameras<16 && cuts>>cameras))return false;
  for(unsigned i=0;i<30;++i)if(!std::isfinite(source_offsets[i]) || source_offsets[i]<0 || source_offsets[i]>600 || (version==1 && source_offsets[i]) || (i<6 && i>=actors && source_offsets[i]))return false;
  double previous[6]={-1,-1,-1,-1,-1,-1};
  for(unsigned i=0;i<32;++i){const auto& k=keys[i];
   if(i>=count){if(k.actor||k.linear||k.at)return false;for(double v:k.pose)if(v)return false;continue;}
   if(k.actor>=actors || k.linear>1 || !std::isfinite(k.at) || k.at<0 || k.at>duration || k.at<=previous[k.actor] || (previous[k.actor]<0 && k.at!=0))return false;
   previous[k.actor]=k.at;
   for(unsigned j=0;j<9;++j)if(!std::isfinite(k.pose[j]) || (j<3?std::abs(k.pose[j])>5000:j<6?std::abs(k.pose[j])>360:k.pose[j]<.001||k.pose[j]>3))return false;
   if(k.pose[6]!=k.pose[7] || k.pose[7]!=k.pose[8])return false;
  }return true;
 }
 bool sample(unsigned actor,double seconds,double* result)const{
  const BlockingKey* a=nullptr;const BlockingKey* b=nullptr;
  for(unsigned i=0;i<count;++i)if(keys[i].actor==actor){if(keys[i].at<=seconds)a=&keys[i];else{b=&keys[i];break;}}
  if(!a)return false;
  const double t=b&&b->linear?std::clamp((seconds-a->at)/(b->at-a->at),0.,1.):0.;
  for(unsigned j=0;j<9;++j){const double delta=b?b->pose[j]-a->pose[j]:0.;result[j]=a->pose[j]+t*(j>=3&&j<6?std::remainder(delta,360.):delta);}return true;
 }
 template<class Plan> bool camera(const Plan& plan,double seconds,double* result)const{
  if(!plan.key_count)return false;
  unsigned a=0,b=0,n=unsigned(plan.key_count);for(unsigned i=1;i<n&&seconds>=plan.keys[i][0];++i)a=i;
  b=seconds<=plan.keys[0][0]?0:std::min(a+1,n-1);
  const double t=a==b||(cuts&(1U<<b))?0.:std::clamp((seconds-plan.keys[a][0])/(plan.keys[b][0]-plan.keys[a][0]),0.,1.);
  for(unsigned j=0;j<7;++j){const double d=plan.keys[b][j+1]-plan.keys[a][j+1];result[j]=plan.keys[a][j+1]+t*(j>=3&&j<6?std::remainder(d,360.):d);}return true;
 }
};
static_assert(sizeof(BlockingKey)==88 && sizeof(SceneCues)==3072,"Scene cue wire layout");
}
