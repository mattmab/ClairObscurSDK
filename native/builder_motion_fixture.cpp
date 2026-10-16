#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstring>
struct CallIdentity {int32_t index=0,serial=0;uint64_t address=0;};
struct Motion {
    CallIdentity selected_{1,1,1},selected_actor_{2,1,2},hover_{1,1,1},hover_actor_{2,1,2};
    bool dragging_=true,carrying_=true,nudging_=true,want_grab_=true,duplicate_requested_=true,left_was_=false;
    bool component_alive=true,actor_alive=true,camera_ok=true,read_ok=true,write_ok=true;
    bool unload_on_read=false,unload_on_write=false,click_active=true;
    int reads=0,writes=0;double position_[3]{},rotation_[3]{},offset_[3]{},depth_=100;
    uint8_t args_[512]{};
    bool call_identity(uint64_t,CallIdentity id){return id.address==1?component_alive:id.address==2?actor_alive:false;}
    void gpu_end_click(){click_active=false;}
    bool camera_pose(uint64_t){return camera_ok;}
    void clear(){std::memset(args_,0,sizeof(args_));}
    bool call(uint64_t,CallIdentity,int){++reads;if(unload_on_read)component_alive=false;return read_ok;}
    bool component_pose(uint64_t,CallIdentity,const uint8_t*){++writes;if(unload_on_write)actor_alive=false;return write_ok;}
    void refresh_candidate(uint64_t,CallIdentity){}
    #include "builder_motion.h"
};
int main(){
    const double forward[]={10,0,0,1,1,0,0,0};
    for(int actor=0;actor<2;++actor){Motion m;if(actor)m.actor_alive=false;else m.component_alive=false;
        assert(m.move(0,forward));assert(m.position_[0]==10);assert(!m.selected_.address&&!m.selected_actor_.address);
        assert(!m.dragging_&&!m.carrying_&&!m.nudging_&&!m.want_grab_&&!m.duplicate_requested_&&m.left_was_);
        assert(!m.click_active&&!m.reads&&!m.writes);}
    Motion read;read.read_ok=false;read.unload_on_read=true;assert(read.move(0,forward));assert(!read.selected_.address);
    Motion write;write.write_ok=false;write.unload_on_write=true;assert(write.move(0,forward));assert(!write.selected_.address);
    Motion live;assert(live.move(0,forward));assert(live.selected_.address&&live.writes==1);
    Motion failure;failure.read_ok=false;assert(!failure.move(0,forward));assert(failure.selected_.address);
    Motion camera;camera.camera_ok=false;assert(!camera.move(0,forward));assert(!camera.reads);
}
