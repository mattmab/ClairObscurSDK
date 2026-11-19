#include "story_inworld_frame.h"
#include <cassert>
#include <cstdio>
using namespace e33_story_inworld;
struct Ops {
 unsigned made=0,released=0;bool release_ready=true;
 bool can_create(){return true;}bool can_release(){return release_ready;}
 void construct(TargetTextValue& out,const TargetStringValue&){out={++made,2,0};}
 bool known_text(const TargetTextValue& value){return value.data&&value.flags==2;}
 void release(TargetTextValue&){++released;}
};
static Packet input(){
 Packet p;p.owner=1;p.ticket=2;p.asset_lease=3;p.system_lease=4;
 for(auto* id:{&p.carrier,&p.asset,&p.system,&p.play,&p.query,&p.interrupt,&p.finished,&p.widget_interrupt})*id={5,6,0x10000};
 p.count=1;p.used_units=2;p.lines[0].text_count=2;p.lines[0].delete_delay=4;p.lines[0].answer_delay=.2;p.units[0]='A';return p;
}
int main(){
 auto p=input();assert(valid(p));
 {Line staging[2]{},engine[2]{};const TargetStringValue source{reinterpret_cast<uint64_t>(staging),2,2};
  assert(!independent_line_array(source,source));
  TargetStringValue copy{reinterpret_cast<uint64_t>(engine),2,2};assert(independent_line_array(copy,source));
  copy.count=1;assert(!independent_line_array(copy,source));copy.count=2;
  copy.capacity=1;assert(!independent_line_array(copy,source));copy.capacity=129;assert(!independent_line_array(copy,source));
  copy={};assert(!independent_line_array(copy,source));}
 {Ops ops;Frame f;assert(f.prepare(ops,p));assert(ops.made==1);assert(f.lines[0].delete_delay==4&&f.lines[0].text.data);
  f.attached=true;assert(!f.cleanup(ops));assert(!ops.released);
  f.attached=false;ops.release_ready=false;assert(!f.cleanup(ops));assert(!ops.released);
  ops.release_ready=true;assert(f.cleanup(ops));assert(ops.released==1);assert(f.cleanup(ops)&&ops.released==1);
  assert(f.prepare(ops,p));assert(f.cleanup(ops));assert(ops.released==2);}
 {Ops ops;Frame f;assert(f.prepare(ops,p));f.unknown=true;assert(!f.cleanup(ops));assert(!ops.released);}
 p.lines[0].character=8;assert(!valid(p));p=input();p.units[1]='X';assert(!valid(p));
 std::puts("In-world frame: ownership, deferred release, quarantine and input validation passed");
}
