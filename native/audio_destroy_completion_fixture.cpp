#include "audio_destroy_completion.h"
#include <cassert>
struct Ops {
 bool allowed=true,held=true,same=true,cls=true,reuse=false;unsigned reads=0,matches_count=0;
 AudioDestroyMarkers value{0x40000000u,0x200000u,0x20,0};
 bool context()const{return allowed;}
 bool owns(uint64_t session,uint64_t token,uint64_t address)const{return held&&session==7&&token==9&&address==0x1000;}
 bool matches(const CallIdentity&){return same&&!(reuse&&++matches_count>1);}
 bool exact_class(const CallIdentity&)const{return cls;}
 AudioDestroyMarkers markers(const CallIdentity&){++reads;return value;}
};
int main(){
 CallIdentity id{17,1001,0x1000};
 auto test=[&](Ops& ops,uint32_t state=2,uint32_t step=1,uint32_t error=202,uint32_t outcome=0,uint32_t detail=0x20200007u,uint64_t session=7,uint64_t token=9){
  return completed_audio_destruction(ops,state,step,error,outcome,detail,session,token,id);
 };
 {Ops ops;assert(test(ops)&&ops.reads==1);}
 for(unsigned failure=0;failure<19;++failure){
  Ops ops;id={17,1001,0x1000};bool result=false;
  switch(failure){
   case 0:result=test(ops,0);break;
   case 1:result=test(ops,2,0);break;
   case 2:result=test(ops,2,1,201);break;
   case 3:result=test(ops,2,1,202,1);break;
   case 4:result=test(ops,2,1,202,2);break;
   case 5:result=test(ops,2,1,202,0,0x20200002);break;
   case 6:id.serial=0;result=test(ops);break;
   case 7:ops.same=false;result=test(ops);break;
   case 8:result=test(ops,2,1,202,0,0x20200007,8);break;
   case 9:ops.held=false;result=test(ops);break;
   case 10:ops.cls=false;result=test(ops);break;
   case 11:ops.allowed=false;result=test(ops);break;
   case 12:ops.value.object_flags=0;result=test(ops);break;
   case 13:ops.value.item_flags=0;result=test(ops);break;
   case 14:ops.value.component_flags=0;result=test(ops);break;
   case 15:ops.value.activity_flags=8;result=test(ops);break;
   case 16:ops.reuse=true;result=test(ops);break;
   case 17:id.address=0;result=test(ops);break;
   case 18:result=test(ops,2,1,202,0,0x20200007,7,0);break;
  }
  assert(!result);if(failure<12||failure>=17)assert(ops.reads==0);
 }
}
