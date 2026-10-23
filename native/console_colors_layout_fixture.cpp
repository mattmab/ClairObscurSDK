#include "console_colors/scrollback_renderer.h"
#include <cassert>
#include <vector>
using namespace ConsoleScrollback;
struct Ops {
 int originals=0,backgrounds=0,inputs=0; bool valid=true;
 std::vector<float> ys;std::vector<Color> colors;
 void original(){++originals;} bool prevalidate(const Frame&){return valid;}
 void background(float,float,float,float,float){++backgrounds;}
 Line line(std::int32_t i){if(i==1)return {L"[READY] ready",13};return {L"Engine",6};}
 float measure_height(Line l){return l.count==13?40.0f:20.0f;}
 void text(Line,float,float y,float,Color c){ys.push_back(y);colors.push_back(c);}
 void original_input(float,float){++inputs;}
};
int main(){
 Frame f;f.width=1920;f.height=1080;f.sample_height=20;f.count=3;f.newest=2;
 Authority a{true,true,true,true,true};Ops o;
 assert(render(a,f,o));assert(o.originals==0 && o.backgrounds==1 && o.inputs==1);
 assert(o.ys.size()==3 && o.ys[0]==790 && o.ys[1]==750 && o.ys[2]==730);
 assert(o.colors[0].r==1 && o.colors[1].g==ConsoleRenderClone::green.g && o.colors[2].r==1);
 Ops p;f.scroll=1;assert(render(a,f,p));assert(p.ys.size()==2 && p.ys[0]==770);
 Ops q;f.scroll=0;f.dpi=2;assert(render(a,f,q));assert(q.ys[0]==800 && q.ys[1]==780);
 Ops denied;a.game_thread=false;assert(!render(a,f,denied));assert(denied.originals==1 && !denied.backgrounds && !denied.inputs);
 a.game_thread=true;a.abi_verified=false;Ops unproved;assert(!render(a,f,unproved));assert(unproved.originals==1);
 a.abi_verified=true;Ops bad;f.dpi=0;assert(!render(a,f,bad));assert(bad.originals==1 && bad.backgrounds==0);
 f.dpi=1;f.count=0;Ops empty;assert(render(a,f,empty));assert(empty.ys.empty() && empty.inputs==1);
}
