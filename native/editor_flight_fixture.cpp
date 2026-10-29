#include "editor_flight_math.h"
#include <cassert>
int main(){
    using namespace e33_editor_flight;
    TickGate gate;assert(gate.due(10.));assert(!gate.due(10.001));assert(!gate.due(10.008));
    assert(gate.due(10.009));assert(gate.due(11.));assert(!gate.due(11.001));
    double fine[6]{};Input held;held.forward=1;
    for(unsigned n=0;n<120;++n)advance(fine,1./120.,held);
    assert(std::abs(fine[0]-1600.)<1e-8);
    double p[6]{};Input i;i.forward=1;advance(p,.05,i);assert(p[0]==80. && p[1]==0.);
    double d[6]{};i.side=1;advance(d,.05,i);assert(std::abs(std::hypot(d[0],d[1])-80.)<1e-8);
    double fast[6]{};i.side=0;i.fast=true;advance(fast,.05,i);assert(fast[0]==320.);
    double clamp[6]{};i.fast=false;advance(clamp,10.,i);assert(clamp[0]==80.);
    i={};i.dx=10000;i.dy=10000;advance(p,.01,i);assert(p[3]==89. && p[4]>=-180. && p[4]<=180.);
    const auto x=p[0];i={};advance(p,.05,i);assert(p[0]==x);
}
