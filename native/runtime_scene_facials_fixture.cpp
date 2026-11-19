#include "runtime_scene_facials.h"
#include <cassert>
#include <limits>
using namespace e33_runtime_scene;
int main(){
 FaceTimeline t{};t.count=2;t.keys[0]={1.f,.2f,0,1,2,.6f};t.keys[1]={1.2f,.3f,0,7,2,.6f};assert(t.valid(2.,2));
 float w[24]{};t.sample(0,1.1,w);assert(w[0]==0 && w[9]>.6f && w[15]>.1f);
 t.sample(0,1.35,w);assert(w[0]>.5f && w[9]==0 && w[17]>.1f);
 t.sample(1,1.35,w);for(float v:w)assert(v==0);
 t.sample(0,0.,w);for(float v:w)assert(v==0);
 t.sample(0,1.1,w);assert(w[9]>.6f); // reverse seek is deterministic
 t.keys[1].at=1.1f;assert(!t.valid(2.,2));t.keys[1].at=1.2f;
 t.keys[1].viseme=255;assert(!t.valid(2.,2));t.keys[1].viseme=7;
 t.keys[1].strength=std::numeric_limits<float>::quiet_NaN();assert(!t.valid(2.,2));
}
