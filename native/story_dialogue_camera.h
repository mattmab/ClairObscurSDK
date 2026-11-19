#pragma once
#include "invocation_protocol.h"
#include <cstring>
namespace e33_story_camera {
constexpr uint32_t operation=234,rejected=3910,uncertain=3911;
#pragma pack(push,1)
struct Packet {
 uint32_t version=3,op=operation,error=0,state=0;
 uint64_t nonce=0,owner=0,camera_owner=0,dialogue_lease=0;
 CallIdentity system{},dialogue{},npc{},camera_npc{},setter{},handler{};
 CallIdentity pose_setter{},pose_getter{};
 CallIdentity view_getter{},view_setter{};
 uint32_t retire=0,reserved=0;
 uint8_t tail[20768]{};
};
#pragma pack(pop)
static_assert(sizeof(Packet)==20984,"Story dialogue camera packet");
inline bool identity(const CallIdentity& id){
 return id.index>=0&&id.serial>0&&id.address>=0x10000&&id.address<=0x7fffffffffffULL&&!(id.address&7);
}
inline bool valid(const Packet& p){
 if(p.version!=3||p.op!=operation||p.error||p.state||p.retire>1||p.reserved||!p.nonce||!p.owner||!p.camera_owner||!p.dialogue_lease||
    !identity(p.system)||!identity(p.dialogue)||!identity(p.npc)||!identity(p.camera_npc)||!identity(p.setter)||!identity(p.handler))return false;
 const bool pose=p.pose_setter.address||p.pose_getter.address;
 if(pose){if(!identity(p.pose_setter)||!identity(p.pose_getter))return false;}
 else if(p.pose_setter.index||p.pose_setter.serial||p.pose_getter.index||p.pose_getter.serial)return false;
 if(p.view_getter.address||p.view_setter.address){
  if(!identity(p.view_getter)||!identity(p.view_setter))return false;
 }else if(p.view_getter.index||p.view_getter.serial||p.view_setter.index||p.view_setter.serial)return false;
 for(auto value:p.tail)if(value)return false;
 return true;
}
// Exact original S_DialogueParameters layout: stage:int32, teleport:bool,
// dialogue cameras:bool, world character:byte, padding. Preserve every byte
// except the camera flag; never reset teleport, forced stage or character.
struct Parameters {uint8_t bytes[8]{};};
inline bool enable_camera(const Parameters& current,Parameters& next){
 if(current.bytes[4]>1||current.bytes[5]>1)return false;
 Parameters result=current;result.bytes[5]=1;next=result;return true;
}
// Original HandleCameraType selects a provided native CameraComponent for
// enum14. All optional movement/soft-object members remain an empty value.
struct CameraArguments {alignas(8) uint8_t bytes[64]{};};
// Spawned carriers must not inherit the tilted, below-ground camera offset
// authored for their original scene. This is local to the owned carrier:
// A wider diagonal shot includes tall cast without putting the player, who
// approaches along the carrier's X axis, directly in front of the camera.
// The camera remains local to its carrier and does not move the NPC/player.
inline void speaker_pose(double (&pose)[12]){
 const double value[12]={0,0,0.9238795325112867,0.3826834323650898,280,-280,50,0,1,1,1,0};
 std::memcpy(pose,value,sizeof(value));
}
inline bool camera_arguments(uint64_t camera,CameraArguments& next){
 if(camera<0x10000||camera>0x7fffffffffffULL||(camera&7))return false;
 CameraArguments result{};result.bytes[0]=14;std::memcpy(result.bytes+8,&camera,8);next=result;return true;
}
inline bool observed_view_allowed(uint64_t current,uint64_t last,uint64_t saved,uint64_t carrier,uint64_t requested=0){
 // StartDialogLines can restore the original, still-owned dialogue carrier
 // between two custom speakers. It is already independently admitted above.
 return current&&(current==last||current==saved||current==carrier||current==requested);
}
inline bool dialogue_pawn_view_allowed(uint64_t current,uint64_t pawn,uint64_t pawn_controller,
                                      uint64_t controller,uint64_t pawn_world,uint64_t world,bool live_identity){
 // Original StartDialogLines restores gameplay's view for a player-speaker
 // line. This exception is valid only inside the independently owned active
 // dialogue, for this local controller's current, same-world possessed pawn.
 return live_identity&&current&&current==pawn&&controller&&pawn_controller==controller&&world&&pawn_world==world;
}
}
