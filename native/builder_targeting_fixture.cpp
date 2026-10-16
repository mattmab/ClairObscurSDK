#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <vector>
static uint64_t clock_ms=1000;
static uint64_t GetTickCount64(){return clock_ms;}
struct CallIdentity {int32_t index=0,serial=0;uint64_t address=0;};
namespace builder_gpu {
struct Bridge {
    uint64_t armed=0,completed=0;float depth=0;
    uint32_t error(){return 0;}
    bool ready(){return true;}
    bool arm(uint64_t id){assert(!armed);armed=id;return true;}
    uint64_t poll(float& sample){const auto id=completed;if(id){sample=depth;completed=armed=0;}return id;}
    void finish(float value){assert(armed);depth=value;completed=armed;}
};
}
struct Picker {
    #include "builder_gpu_state.h"
    struct Candidate {CallIdentity actor,component;double low[3],high[3],pose[12];};
    std::vector<Candidate> candidates_;
    CallIdentity ids_[1]{};
    uint8_t args_[512]{};
    int render_mode=0,captures=0;
    double projected_offset=0;
    uint64_t shown=0;
    void clear(){std::memset(args_,0,sizeof(args_));}
    template<class T> T get(size_t offset=0){T v{};std::memcpy(&v,args_+offset,sizeof(v));return v;}
    template<class T> void put(size_t offset,T value){std::memcpy(args_+offset,&value,sizeof(value));}
    bool call_identity(uint64_t,CallIdentity id){return id.address!=0;}
    bool gpu_setting(uint64_t,const char*,uint64_t value){render_mode=int(value);return true;}
    bool call(uint64_t,CallIdentity,int fn){
        if(fn==32){put(0,int32_t(100));put(4,int32_t(100));}
        if(fn==24){put(24,50.+projected_offset);put(32,50.);args_[41]=1;}
        if(fn==5)args_[305]=1;
        if(fn==42)shown=get<uint64_t>();
        if(fn==43)shown=0;
        if(fn==41)++captures;
        return true;
    }
    static void inverse_rotate(const double*,const double* v,double* out){std::memcpy(out,v,24);}
    #include "builder_gpu_pick.h"
    void add(uint64_t id,double entry){
        Candidate c{};c.actor.address=c.component.address=id;c.low[0]=entry;c.high[0]=1000;
        c.low[1]=c.low[2]=-1;c.high[1]=c.high[2]=1;c.pose[3]=1;c.pose[8]=c.pose[9]=c.pose[10]=1;candidates_.push_back(c);
    }
    uint64_t tick(double x=0,double yaw=0){
        const double origin[]={x,0,0},dir[]={std::cos(yaw),std::sin(yaw),0};CallIdentity actor{},component{};double distance=200000;
        ++clock_ms;assert(gpu_pick(0,origin,dir,actor,component,distance));return component.address;
    }
};
int main(){
    // Thirty-two empty bounds must not hide the actual foreground surface.
    Picker many;for(uint64_t id=1;id<=40;++id)many.add(id,double(id));
    assert(!many.tick());assert(many.render_mode==1);
    many.gpu_bridge_.finish(500);assert(!many.tick());assert(many.gpu_candidates_.size()==40);
    for(int id=1;id<=40;++id){assert(many.shown==uint64_t(id));many.gpu_bridge_.finish(id==40?500.f:100000000.f);const auto hit=many.tick();assert(hit==(id==40?40u:0u));}
    // The old result cannot seed the next query: the prop disappeared.
    many.gpu_bridge_.finish(100000000);many.tick();
    for(int id=1;id<=40;++id){many.gpu_bridge_.finish(100000000);many.tick();}
    assert(!many.gpu_ready_component_.address);
    // A non-editable foreground model must block the selectable prop behind it.
    Picker blocked;blocked.add(1,100);blocked.tick();blocked.gpu_bridge_.finish(50);assert(!blocked.tick());assert(!blocked.gpu_ready_component_.address);
    // Never change the capture list while a readback still owns the target.
    Picker pending;pending.add(1,10);pending.tick();const auto captures=pending.captures;
    pending.tick();pending.tick();assert(pending.captures==captures);
    // Camera movement invalidates pending results, even when the old point
    // projects onto the center again (moving forward on the same ray).
    pending.gpu_bridge_.finish(50);assert(!pending.tick(30));assert(!pending.gpu_ready_component_.address);assert(pending.render_mode==1);
    // Prioritize a likely mesh, but require its actual GPU surface. Exact
    // foreground depth completes without visiting overlapping empty bounds.
    Picker preferred;preferred.add(1,10);preferred.add(2,20);preferred.add(3,30);
    preferred.gpu_preferred_component_.address=3;
    preferred.tick();preferred.gpu_bridge_.finish(500);preferred.tick();assert(preferred.shown==3);
    preferred.gpu_bridge_.finish(500);assert(preferred.tick()==3);assert(preferred.captures==3);
    // A misleading collision hint must not select a surface behind foreground.
    Picker misleading;misleading.add(1,10);misleading.add(2,20);misleading.gpu_preferred_component_.address=2;
    misleading.tick();misleading.gpu_bridge_.finish(50);misleading.tick();assert(misleading.shown==2);
    misleading.gpu_bridge_.finish(80);assert(!misleading.tick());assert(misleading.shown==1);
    misleading.gpu_bridge_.finish(50);assert(misleading.tick()==1);
    // Continuous small movement must not starve a two-capture query.
    Picker moving;moving.add(1,10);moving.tick();moving.gpu_bridge_.finish(500);
    moving.tick(2);assert(moving.render_mode==2);moving.gpu_bridge_.finish(500);
    assert(moving.tick(4)==1);assert(moving.tick(6)==1);
    // Small continuous mouse turns finish rather than cancelling every frame.
    Picker turning;turning.add(1,10);turning.tick();turning.gpu_bridge_.finish(500);
    turning.projected_offset=2;turning.tick(0,.002);turning.gpu_bridge_.finish(500);
    turning.projected_offset=4;assert(turning.tick(0,.004)==1);
    // Reprojection outside the small crosshair aperture rejects the old hit.
    moving.projected_offset=9;assert(!moving.tick(6));moving.projected_offset=0;
    // A near surface cannot be reused after moving a large fraction of its depth.
    Picker near;near.add(1,10);near.tick();near.gpu_bridge_.finish(50);near.tick(2);
    near.gpu_bridge_.finish(50);assert(!near.tick(4));
    // Published results expire even when the view remains centered.
    clock_ms+=151;assert(!moving.tick(6));
    // A click owns its original ray even while the live view turns away.
    Picker clicked;clicked.add(1,10);const double clickOrigin[]={0.,0.,0.},clickDir[]={1.,0.,0.};
    clicked.gpu_begin_click(clickOrigin,clickDir);clicked.tick();
    clicked.gpu_bridge_.finish(500);clicked.projected_offset=100;clicked.tick();
    clicked.gpu_bridge_.finish(500);assert(clicked.tick()==1);
    clicked.gpu_end_click();assert(!clicked.tick());
    // A fresh click cannot reuse a previous hover capture.
    clicked.gpu_begin_click(clickOrigin,clickDir);assert(!clicked.tick());
    puts("PASS: >32 candidates, vanished hits, foreground occlusion, capture ownership, moved camera");
}
