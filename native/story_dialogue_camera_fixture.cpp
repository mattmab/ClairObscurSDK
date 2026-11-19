#include "story_dialogue_camera.h"
#include <cassert>
#include <cstdio>
#include <cmath>
int main(){
 using namespace e33_story_camera;
 assert(observed_view_allowed(0x10000,0x10000,0x20000,0x30000));
 assert(observed_view_allowed(0x20000,0x10000,0x20000,0x30000));
 assert(observed_view_allowed(0x30000,0x10000,0x20000,0x30000));
 assert(!observed_view_allowed(0x40000,0x10000,0x20000,0x30000));
 assert(!observed_view_allowed(0,0,0,0));
 assert(observed_view_allowed(0x40000,0x10000,0x20000,0x30000,0x40000));
 assert(!observed_view_allowed(0x50000,0x10000,0x20000,0x30000,0x40000));
 assert(dialogue_pawn_view_allowed(0x40000,0x40000,0x50000,0x50000,0x60000,0x60000,true));
 assert(!dialogue_pawn_view_allowed(0x40008,0x40000,0x50000,0x50000,0x60000,0x60000,true));
 assert(!dialogue_pawn_view_allowed(0x40000,0x40000,0x50008,0x50000,0x60000,0x60000,true));
 assert(!dialogue_pawn_view_allowed(0x40000,0x40000,0x50000,0x50000,0x60008,0x60000,true));
 assert(!dialogue_pawn_view_allowed(0x40000,0x40000,0x50000,0x50000,0x60000,0x60000,false));
 assert(!dialogue_pawn_view_allowed(0,0,0x50000,0x50000,0x60000,0x60000,true));
 assert(!dialogue_pawn_view_allowed(0x40000,0x40000,0,0,0x60000,0x60000,true));
 assert(!dialogue_pawn_view_allowed(0x40000,0x40000,0x50000,0x50000,0,0,true));
 for(unsigned teleport=0;teleport<2;++teleport)for(unsigned camera=0;camera<2;++camera)for(unsigned character=0;character<256;++character){
  Parameters before{},after{};
  before.bytes[0]=0xff;before.bytes[1]=0x12;before.bytes[2]=0x34;before.bytes[3]=0x56;
  before.bytes[4]=uint8_t(teleport);before.bytes[5]=uint8_t(camera);before.bytes[6]=uint8_t(character);before.bytes[7]=0xa5;
  assert(enable_camera(before,after));
  for(unsigned i=0;i<8;++i)assert(after.bytes[i]==(i==5?1:before.bytes[i]));
 }
 Parameters invalid{},untouched{};invalid.bytes[4]=2;untouched.bytes[0]=0x55;
 assert(!enable_camera(invalid,untouched)&&untouched.bytes[0]==0x55);
 invalid.bytes[4]=0;invalid.bytes[5]=2;assert(!enable_camera(invalid,untouched));
 CameraArguments args{};assert(camera_arguments(0x10000,args));
 assert(args.bytes[0]==14);uint64_t value=0;std::memcpy(&value,args.bytes+8,8);assert(value==0x10000);
 for(unsigned i=1;i<64;++i)if(i<8||i>=16)assert(args.bytes[i]==0);
 args.bytes[0]=99;assert(!camera_arguments(0x10001,args)&&args.bytes[0]==99);
 Packet p;p.nonce=1;p.owner=2;p.camera_owner=3;p.dialogue_lease=4;
 p.system={1,2,0x10000};p.dialogue={2,3,0x20000};p.npc={3,4,0x30000};
 p.camera_npc={4,5,0x40000};p.setter={5,6,0x50000};p.handler={6,7,0x60000};
 assert(valid(p));p.tail[20767]=1;assert(!valid(p));p.tail[20767]=0;
 p.retire=1;assert(valid(p));p.retire=2;assert(!valid(p));p.retire=0;
 p.reserved=1;assert(!valid(p));p.reserved=0;
 p.pose_setter={7,8,0x70000};assert(!valid(p));
 p.pose_getter={8,9,0x80000};assert(valid(p));
 p.pose_setter={};p.pose_getter={};
 p.view_getter={9,10,0x90000};assert(!valid(p));
 p.view_setter={10,11,0xa0000};assert(valid(p));p.view_getter={};p.view_setter={};
 double pose[12]{};speaker_pose(pose);
 assert(pose[4]==280&&pose[5]==-280&&pose[6]==50&&pose[8]==1&&pose[9]==1&&pose[10]==1);
 assert(std::fabs(pose[2]*pose[2]+pose[3]*pose[3]-1)<1e-12);
 // Local camera forward points back toward the carrier, with lateral
 // separation from the player's approach axis rather than a straight shot.
 const double forward_x=1-2*pose[2]*pose[2],forward_y=2*pose[2]*pose[3];
 assert(forward_x*pose[4]+forward_y*pose[5]<-395);
 p.camera_owner=0;assert(!valid(p));p.camera_owner=3;p.dialogue.serial=0;assert(!valid(p));
 std::puts("Story camera packet, parameter preservation and original camera argument policy passed");
}
