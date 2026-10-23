#include "arena_approach_policy.h"
#include <cassert>
#include <cstdio>
#include <limits>
struct Queries {
    unsigned surfaces=0,volumes=0;
    int mode=0;
    e33_surface_query::Result surface(const double* a,const double*,e33_surface_query::Sample& out){
        ++surfaces;out.point[0]=a[0];out.point[1]=a[1];out.point[2]=0;out.normal[2]=1;
        if(mode==1&&a[0]>=400&&a[0]<=600)return e33_surface_query::Result::NoHit;
        if(mode==2&&a[0]>800)out.point[2]=200;
        if(mode==3)out.normal[2]=.5;
        if(mode==4)return e33_surface_query::Result::Rejected;
        if(mode==5)out.point[2]=a[0]*.05;
        if(mode==6&&a[0]>800)out.point[2]=50;
        if(mode==7)out.point[2]=std::numeric_limits<double>::quiet_NaN();
        if(mode==10)out.point[2]=a[0]*.1;
        if(mode==11)out.point[2]=150.;
        return e33_surface_query::Result::Hit;
    }
    e33_volume_query::Result volume(const double* center,const double*){
        ++volumes;
        if(mode==8&&center[0]>800)return e33_volume_query::Result::Blocked;
        if(mode==9)return e33_volume_query::Result::Rejected;
        return e33_volume_query::Result::Clear;
    }
};
int main(){
    const double pawn[]={0,0,100},target[]={1600,0,0},half[]={40,40,100};
    const double offset[]={455,-162};double xy[2]{};
    assert(e33_arena_approach::origin(pawn,0,1600,offset,xy));
    assert(xy[0]+offset[0]==1600&&xy[1]+offset[1]==0);
    assert(e33_arena_approach::origin(pawn,90,1600,offset,xy));
    assert(std::abs(xy[0]+offset[0])<1.e-8&&std::abs(xy[1]+offset[1]-1600)<1.e-8);
    // Source Visages frames: a 60-degree fallback translation without rotating
    // the assembly puts its small entry sphere off the visible-body approach.
    // Compare that failure geometry with anchoring the original slot ahead.
    const double source_slot[]={454.9899677219329,-162.12084800465288};
    const double source_body[]={11280.77860380239,-778.6775812619694};
    auto body_ray_miss=[&](const double* root){
        const double ex=root[0]+source_slot[0],ey=root[1]+source_slot[1];
        const double bx=root[0]+source_body[0],by=root[1]+source_body[1];
        return std::abs(ex*by-ey*bx)/std::hypot(bx,by);
    };
    const double sideways[]={800.,1600.*std::sqrt(.75)};
    assert(body_ray_miss(sideways)>300.);
    assert(e33_arena_approach::origin(pawn,0,1600,source_slot,xy));
    assert(body_ray_miss(xy)<100.);
    unsigned samples=0;Queries good;
    assert(e33_arena_approach::corridor(good,pawn,target,half,0,samples)==e33_arena_approach::Result::Supported);
    assert(samples==195&&good.volumes==65);
    for(int mode:{1,2,3,6,8}){
        Queries q;q.mode=mode;
        assert(e33_arena_approach::corridor(q,pawn,target,half,0,samples)==e33_arena_approach::Result::Unsupported);
    }
    for(int mode:{4,7,9}){
        Queries q;q.mode=mode;
        assert(e33_arena_approach::corridor(q,pawn,target,half,0,samples)==e33_arena_approach::Result::Rejected);
    }
    Queries slope;slope.mode=5;
    assert(e33_arena_approach::corridor(slope,pawn,target,half,80,samples)==e33_arena_approach::Result::Supported);
    Queries mismatch;
    assert(e33_arena_approach::corridor(mismatch,pawn,target,half,400,samples)==e33_arena_approach::Result::Unsupported);
    const double far[]={4000,0,0};Queries invalid;
    assert(e33_arena_approach::corridor(invalid,pawn,far,half,0,samples)==e33_arena_approach::Result::Rejected);
    assert(invalid.surfaces==0);
    // Diagnostics must expose the actual refusal without changing decisions
    // or the number/order of engine queries, including the strict net-rise cap.
    const e33_arena_approach::Reason expected[]={
        e33_arena_approach::Reason::Supported,e33_arena_approach::Reason::NoSurface,
        e33_arena_approach::Reason::Step,e33_arena_approach::Reason::Slope,
        e33_arena_approach::Reason::SurfaceRejected,e33_arena_approach::Reason::Supported,
        e33_arena_approach::Reason::Step,e33_arena_approach::Reason::SurfaceRejected,
        e33_arena_approach::Reason::Blocked,e33_arena_approach::Reason::ClearanceRejected,
        e33_arena_approach::Reason::TotalHeight,e33_arena_approach::Reason::StartHeight};
    for(int mode=0;mode<12;++mode){
        Queries original,observed;original.mode=observed.mode=mode;
        e33_arena_approach::Diagnostic diagnostic{};unsigned old_samples=0,new_samples=0;
        const auto old_result=e33_arena_approach::corridor(original,pawn,target,half,0,old_samples);
        const auto new_result=e33_arena_approach::corridor(observed,pawn,target,half,0,new_samples,&diagnostic);
        assert(old_result==new_result&&old_samples==new_samples);
        assert(original.surfaces==observed.surfaces&&original.volumes==observed.volumes);
        assert(diagnostic.reason==static_cast<uint32_t>(expected[mode]));
        if(mode==10){assert(diagnostic.step==41);assert(diagnostic.observed==102.5&&diagnostic.reference==0.);}
    }
    e33_arena_approach::Diagnostic mismatch_detail{};Queries end_query;
    assert(e33_arena_approach::corridor(end_query,pawn,target,half,400,samples,&mismatch_detail)==e33_arena_approach::Result::Unsupported);
    assert(mismatch_detail.reason==static_cast<uint32_t>(e33_arena_approach::Reason::EndHeight));
    assert(e33_arena_approach::permits_placement(e33_arena_approach::Result::Supported,true));
    assert(!e33_arena_approach::permits_placement(e33_arena_approach::Result::Unsupported,true));
    assert(e33_arena_approach::permits_placement(e33_arena_approach::Result::Unsupported,false));
    assert(!e33_arena_approach::permits_placement(e33_arena_approach::Result::Rejected,false));
    std::puts("Arena forward anchor and sampled corridor: flat/slope accepted; hole, cliff, step, obstruction and stale query refused");
}
