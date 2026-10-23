#include "enemy_ground_search.h"
#include <cassert>
#include <limits>
#include <cstdio>
#include <initializer_list>

int main(){
    using namespace e33_enemy_ground;
    const double origin[]={100.,200.};double chosen[]={-1.,-1.};unsigned calls=0;
    auto result=search(origin,0.,1000.,[&](const double* point){
        ++calls;assert(std::abs(std::hypot(point[0]-100.,point[1]-200.)-1000.)<1.e-8);
        assert(point[0]>100.);return calls==3?Support::Accepted:Support::Unsupported;
    },chosen);
    assert(result==Support::Accepted&&calls==3&&chosen[1]>200.);
    calls=0;chosen[0]=-1.;chosen[1]=-1.;
    result=search(origin,0.,1000.,[&](const double*){++calls;return Support::Unsupported;},chosen);
    assert(result==Support::Unsupported&&calls==9&&chosen[0]==-1.&&chosen[1]==-1.);
    calls=0;
    result=search(origin,0.,1000.,[&](const double*){++calls;return Support::Rejected;},chosen);
    assert(result==Support::Rejected&&calls==1&&chosen[0]==-1.);
    calls=0;
    for(const auto distance:{0.,-1.,200001.,std::numeric_limits<double>::infinity()}){
        result=search(origin,0.,distance,[&](const double*){++calls;return Support::Accepted;},chosen);
        assert(result==Support::Rejected&&calls==0);
    }
    puts("Ground search fixture passed: bounded probes, full separation, forward sector, no partial result, fail closed.");
}
