#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
namespace e33_runtime_scene {
inline constexpr const char* face_shapes[]={"jaw_open","mouth_funnel_DL","mouth_funnel_DR","mouth_funnel_UL","mouth_funnel_UR","mouth_stretch_left","mouth_stretch_right","mouth_lowerLipBite_L","mouth_lowerLipBite_R","mouth_press_DL","mouth_press_DR","mouth_press_UL","mouth_press_UR","mouth_cornerPull_left","mouth_cornerPull_right","mouth_cornerDepress_L","mouth_cornerDepress_R","brow_raiseIn_L","brow_raiseIn_R","brow_down_L","brow_down_R","eye_blink_L","eye_blink_R","jaw_clench_L"};
struct FaceKey {float at=0,duration=0;uint16_t actor=0;uint8_t viseme=0,emotion=0;float strength=0;};
struct FaceTimeline {
 uint32_t count=0;FaceKey keys[768]{};
 bool valid(double duration,unsigned actors)const{
  if(count>768 || actors>6)return false;
  double previous[6]={-1,-1,-1,-1,-1,-1};
  for(unsigned i=0;i<768;++i){const auto& k=keys[i];
   if(i>=count){if(k.at||k.duration||k.actor||k.viseme||k.emotion||k.strength)return false;continue;}
   if(k.actor>=actors||k.viseme>10||k.emotion>5||!std::isfinite(k.at)||!std::isfinite(k.duration)||!std::isfinite(k.strength)||k.at<0||k.duration<.02f||k.duration>30||double(k.at)+k.duration>duration+.0001||k.at<previous[k.actor]-.0001||k.strength<0||k.strength>1)return false;
   previous[k.actor]=double(k.at)+k.duration;
  }return true;
 }
 static void mouth(unsigned kind,float* w,float gain){
  float jaw=0,funnel=0,stretch=0,bite=0,press=0;
  switch(kind){case 1:press=.65f;break;case 2:jaw=.06f;bite=.6f;break;case 3:jaw=.17f;stretch=.12f;break;case 4:jaw=.12f;stretch=.18f;break;case 5:jaw=.2f;funnel=.22f;break;case 6:jaw=.14f;funnel=.36f;break;case 7:jaw=.55f;break;case 8:jaw=.2f;stretch=.42f;break;case 9:jaw=.35f;funnel=.55f;break;case 10:jaw=.1f;funnel=.7f;break;default:break;}
  w[0]+=gain*jaw;for(unsigned j=1;j<=4;++j)w[j]+=gain*funnel;
  for(unsigned j=5;j<=6;++j)w[j]+=gain*stretch;for(unsigned j=7;j<=8;++j)w[j]+=gain*bite;for(unsigned j=9;j<=12;++j)w[j]+=gain*press;
 }
 void sample(unsigned actor,double seconds,float* w)const{
  std::fill(w,w+24,0.f);float emotions[6]{};
  for(unsigned i=0;i<count;++i){const auto& k=keys[i];if(k.actor!=actor)continue;
   const double start=k.at,end=start+k.duration;
   if(seconds>=start-.03 && seconds<end+.03){const auto gain=float(std::clamp(std::min((seconds-start+.03)/.06,(end+.03-seconds)/.06),0.,1.));mouth(k.viseme,w,gain);}
   const auto feeling=float(std::clamp(std::min((seconds-start+.2)/.25,(end+.2-seconds)/.25),0.,1.))*k.strength;
   emotions[k.emotion]=std::max(emotions[k.emotion],feeling);
  }
  w[13]=w[14]=.35f*emotions[1];w[15]=w[16]=.3f*emotions[2];
  w[17]=w[18]=std::max(.4f*emotions[2],std::max(.3f*emotions[3],.55f*emotions[4]));
  w[19]=w[20]=.4f*emotions[5];
  for(unsigned i=0;i<24;++i)w[i]=std::clamp(w[i],0.f,1.f);
 }
};
static_assert(sizeof(FaceKey)==16,"Face key wire size");
}
