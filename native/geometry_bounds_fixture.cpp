#include "geometry_bounds.h"
#include <cassert>
#include <limits>
#include <cstdio>
int main(){
    e33_geometry::BoundsUnion bounds;double center[3]{},extent[3]{};
    assert(!bounds.result(center,extent));
    const double a[]={10,20,30},ae[]={1,2,3},b[]={20,10,40},be[]={2,3,4};
    assert(bounds.add(a,ae)&&bounds.add(b,be)&&bounds.result(center,extent));
    assert(center[0]==15.5&&extent[0]==6.5&&center[1]==14.5&&extent[1]==7.5&&center[2]==35.5&&extent[2]==8.5);
    const double zero[]={0,0,0},bad[]={1,-1,1},nan[]={0,0,std::numeric_limits<double>::quiet_NaN()};
    assert(bounds.add(a,zero)&&bounds.count==2);
    assert(!bounds.add(a,bad)&&!bounds.add(nan,ae)&&bounds.count==2);
    assert(bounds.result(center,extent)&&center[0]==15.5);
    puts("Geometry bounds fixture passed: full mesh union, empty geometry, invalid/nonfinite rejection, no partial invalid accumulation.");
}
