#include <cstdint>
#include <cmath>
#include <utility>
#include <cassert>
#include <limits>
#include "runtime_scene_plan.h"
#include "runtime_scene_input.h"
#include "runtime_scene_timeline.h"
int main(){
    e33_runtime_scene::Plan p{};p.magic=0x314e4353;p.version=6;p.duration=20.;p.count=3.;p.roles[1]=1.;p.roles[2]=2.;p.bindings[1]=1.;p.bindings[2]=2.;
    for(auto& pose:p.poses)pose[6]=pose[7]=pose[8]=1.;
    p.camera[0]=500.;p.camera[1]=70.;p.camera[2]=165.;p.camera[3]=45.;p.camera[4]=2.;p.camera[5]=18.;p.camera[6]=50.;
    assert(p.valid());auto bad=p;bad.duration=0.;assert(!bad.valid());
    bad=p;bad.audio[4]=20.;assert(!bad.valid());bad=p;bad.poses[1][2]=std::numeric_limits<double>::quiet_NaN();assert(!bad.valid());
    bad=p;bad.poses[0][7]=2.;assert(!bad.valid());bad=p;bad.camera[5]=1.;assert(!bad.valid());
    bad=p;bad.count=7.;assert(!bad.valid());bad=p;bad.clips[0]=double(e33_runtime_scene::scene_clip_count);assert(!bad.valid());
    bad=p;bad.loops[0]=.5;assert(!bad.valid());bad=p;bad.bindings[1]=0.;assert(!bad.valid());
    bad=p;bad.bindings[0]=-1.;assert(!bad.valid());
    for(auto* times:{p.audio,p.impact,p.recoil,p.trail})for(unsigned i=0;i<(times==p.trail?2U:9U);++i)times[i]=-1.;
    p.count=0.;for(auto& binding:p.bindings)binding=-1.;assert(p.valid());
    p.key_count=2.;p.keys[0][0]=2.;p.keys[0][4]=10.;p.keys[0][5]=170.;p.keys[0][7]=50.;p.keys[1][0]=10.;p.keys[1][1]=80.;p.keys[1][4]=30.;p.keys[1][5]=-170.;p.keys[1][7]=70.;assert(p.valid());
    double camera[7]{};assert(p.camera_pose(6.,camera));assert(camera[0]==40. && camera[3]==20. && camera[4]==180. && camera[6]==60.);
    assert(p.camera_pose(0.,camera) && camera[4]==170.);assert(p.camera_pose(20.,camera) && camera[0]==80.);
    bad=p;bad.keys[1][0]=2.;assert(!bad.valid());bad=p;bad.keys[2][0]=1.;assert(!bad.valid());
    bad=p;bad.keys[1][7]=121.;assert(!bad.valid());bad=p;bad.key_count=17.;assert(!bad.valid());
    p.count=6.;for(auto& clip:p.clips)clip=2.;for(auto& loop:p.loops)loop=1.;assert(p.valid());
    e33_runtime_scene::TimelineDrag drag;double seek=0.;auto x=[](double at){return .08+.84*at/20.;};
    p.animation[0]=p.animation[1]=2.;
    assert(drag.sample(p,1,true,x(2.),.875,1920.,seek));assert(drag.kind==1 && drag.index==1);
    assert(drag.sample(p,1,true,x(5.),.875,1920.,seek));assert(p.animation[1]==5. && p.animation[0]==2. && p.valid());
    assert(!drag.sample(p,1,false,x(5.),.875,1920.,seek));
    assert(drag.sample(p,1,true,x(9.),.875,1920.,seek));assert(drag.kind==0 && seek==9. && p.animation[1]==5.);
    drag.sample(p,1,false,x(9.),.875,1920.,seek);
    for(auto& at:p.audio)at=-1.;p.audio[9]=4.;
    assert(drag.sample(p,1,true,x(4.),.90,1920.,seek));assert(drag.kind==2);
    assert(drag.sample(p,1,true,x(100.),.90,1920.,seek));assert(p.audio[9]<p.duration && p.valid());
    assert(drag.sample(p,1,true,x(-100.),.90,1920.,seek));assert(p.audio[9]==0.);
    drag.sample(p,1,false,x(0.),.90,1920.,seek);
    assert(drag.sample(p,1,true,x(2.),.925,1920.,seek));assert(drag.camera_selected==0);
    assert(drag.sample(p,1,true,x(15.),.925,1920.,seek));assert(p.keys[0][0]<p.keys[1][0] && p.valid());
    drag.cancel();const auto saved=p.keys[0][0];assert(!drag.sample(p,1,true,x(1.),.925,1920.,seek));assert(p.keys[0][0]==saved);
    p.extra_count=3.;p.extra[0][0]=1.;p.extra[0][1]=3.;p.extra[0][2]=1.;p.extra[1][0]=1.;p.extra[1][1]=8.;p.extra[1][2]=2.;p.extra[2][0]=0.;p.extra[2][1]=6.;
    assert(p.valid());assert(p.active_animation(1,2.)==1);assert(p.active_animation(1,4.)==6);assert(p.active_animation(1,7.)==1);assert(p.active_animation(1,9.)==7);assert(p.active_animation(0,9.)==8);
    drag.sample(p,1,false,x(3.),.875,1920.,seek);assert(drag.sample(p,1,true,x(3.),.875,1920.,seek));assert(drag.index==6);
    assert(drag.sample(p,1,true,x(10.),.875,1920.,seek));assert(p.extra[0][1]==10. && p.animation[1]==5. && p.extra[1][1]==8. && p.valid());assert(p.active_animation(1,11.)==6);
    bad=p;bad.extra_count=25.;assert(!bad.valid());bad=p;bad.extra[0][0]=6.;assert(!bad.valid());bad=p;bad.extra[0][2]=double(e33_runtime_scene::scene_clip_count);assert(!bad.valid());
    p.extra[0][0]=0.;p.extra[0][1]=p.extra[0][2]=-1.;p.extra[0][3]=0.;assert(p.valid());assert(p.active_animation(1,11.)==7);
    p.animation[1]=p.clips[1]=-1.;assert(p.valid());assert(p.active_animation(1,1.)==1);assert(p.active_animation(1,9.)==7);
    p.gains[9]=2.;assert(p.valid());bad=p;bad.gains[9]=2.01;assert(!bad.valid());bad=p;bad.gains[0]=-.01;assert(!bad.valid());
    drag.sample(p,1,false,x(1.),.875,1920.,seek);assert(drag.sample(p,1,true,x(1.),.875,1920.,seek));assert(drag.kind==0);
    auto editable=p;editable.key_count=0.;for(auto& row:editable.keys)for(double& v:row)v=0.;
    assert(editable.editable_camera_key(3.01)==0);assert(editable.key_count==1. && editable.keys[0][0]==3.);
    assert(editable.editable_camera_key(3.)==0 && editable.key_count==1.);
    editable.keys[0][1]=123.;assert(editable.editable_camera_key(1.)==0);assert(editable.keys[1][1]==123. && editable.valid());
    for(int j=4;j<18;++j)assert(editable.editable_camera_key(double(j))>=0);
    assert(editable.key_count==16.);const auto full=editable;assert(editable.editable_camera_key(19.)==-1);
    assert(editable.key_count==full.key_count && editable.valid());

    auto viewplan=p;viewplan.key_count=0.;for(auto& row:viewplan.keys)for(auto& v:row)v=0.;
    viewplan.anchor[0]=100.;viewplan.anchor[1]=200.;viewplan.anchor[2]=50.;viewplan.anchor[3]=90.;
    const double eye[]={300.,400.,500.,15.,170.,20.};std::copy(eye,eye+6,viewplan.editor_camera);
    assert(viewplan.capture_editor_camera(3.01,90.)==0);assert(viewplan.key_count==1. && viewplan.keys[0][0]==3.);
    double world[7]{};viewplan.camera_world(3.,world);for(unsigned i=0;i<6;++i)assert(std::abs(world[i]-eye[i])<.00001);assert(world[6]==90.);
    viewplan.editor_camera[0]+=20.;assert(viewplan.capture_editor_camera(3.,55.)==0 && viewplan.key_count==1.);
    viewplan.editor_camera[0]=1.e7;assert(viewplan.capture_editor_camera(4.,55.)==-1 && viewplan.key_count==1.);
    assert(viewplan.valid());

    auto tiny=p;for(unsigned axis=6;axis<9;++axis)tiny.poses[0][axis]=.001;assert(tiny.valid());
    tiny.poses[0][6]=.0009;assert(!tiny.valid());

    e33_runtime_scene::GameplayShortcutFilter shortcuts;
    for(unsigned key:{'Z','M','G'}){
        assert(!shortcuts.consume(key,true,false,false)); // gameplay/text entry
        assert(shortcuts.consume(key,true,false,true));
    }
    assert(!shortcuts.consume('W',true,false,true));
    for(unsigned key:{'M','Z','G'}){
        assert(shortcuts.consume(key,true,false,false)); // independent held repeats
        assert(shortcuts.consume(key,false,true,false)); // release after exit
        assert(!shortcuts.consume(key,true,false,false));
        assert(!shortcuts.consume(key,false,true,false));
    }

}
