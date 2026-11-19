#include <cmath>
#include <cassert>
#include <limits>
#include "runtime_scene_plan.h"
#include "runtime_scene_cues.h"
int main(){
 using namespace e33_runtime_scene;SceneCues c{};c.magic=0x31514353;c.version=1;c.count=2;
 for(unsigned i=0;i<2;++i){c.keys[i].pose[6]=c.keys[i].pose[7]=c.keys[i].pose[8]=1.;}
 c.keys[1].at=10.;c.keys[1].pose[0]=100.;c.keys[0].pose[4]=170.;c.keys[1].pose[4]=-170.;
 assert(c.valid(20.,1,2));double value[9]{};assert(c.sample(0,5.,value)&&value[0]==0.);
 c.keys[1].linear=1;assert(c.sample(0,5.,value)&&value[0]==50.&&value[4]==180.);
 assert(c.sample(0,10.,value)&&value[0]==100.);assert(c.sample(0,0.,value)&&value[0]==0.);
 auto bad=c;bad.keys[1].actor=6;assert(!bad.valid(20.,1,2));bad=c;bad.keys[1].at=0;assert(!bad.valid(20.,1,2));
 bad=c;bad.keys[0].at=1.;assert(!bad.valid(20.,1,2));bad=c;bad.keys[1].pose[0]=std::numeric_limits<double>::quiet_NaN();assert(!bad.valid(20.,1,2));
 Plan p{};p.key_count=2;p.keys[0][0]=0;p.keys[1][0]=10;p.keys[1][1]=100.;double camera[7]{};
 c.cuts=2;assert(c.camera(p,9.,camera)&&camera[0]==0.);assert(c.camera(p,10.,camera)&&camera[0]==100.);
 c.cuts=0;assert(c.camera(p,5.,camera)&&camera[0]==50.);
 c.source_offsets[0]=40.;assert(!c.valid(20.,1,2));c.version=2;assert(c.valid(20.,1,2));
 c.source_offsets[1]=1.;assert(!c.valid(20.,1,2));c.source_offsets[1]=0.;
 c.source_offsets[0]=std::numeric_limits<double>::quiet_NaN();assert(!c.valid(20.,1,2));
}

