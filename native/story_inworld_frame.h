#pragma once
#include "story_inworld_packet.h"
#include <cstddef>
namespace e33_story_inworld {
struct Line {
 uint8_t character=0,emotion=0,padding_2[6]{};double delete_delay=0,answer_delay=0;
 uint8_t use_sound_duration=0,padding_25[7]{};uint64_t wave=0;
 uint8_t portrait_right=0,padding_41[7]{};uint64_t table=0,row=0;
 TargetTextValue text{};uint64_t sound=0;
};
static_assert(sizeof(Line)==88,"Original S_DialogueLine extent");
static_assert(offsetof(Line,text)==64,"Original in-world FText slot");
// A UObject property must never own the session's staging buffer. Copying it
// through FArrayProperty gives both the array and its FText values engine
// ownership, including when forced world purge runs before Python retirement.
inline bool independent_line_array(const TargetStringValue& copy,const TargetStringValue& source){
 return copy.data&&!(copy.data&7)&&copy.data!=source.data&&copy.count==source.count&&
  copy.count>0&&copy.capacity>=copy.count&&copy.capacity<=128;
}
struct Frame {
 OwnedTextStorage owners[capacity];Line lines[capacity]{};TargetStringValue array{};
 uint32_t count=0;bool prepared=false,attached=false,unknown=false;
 template<class Ops> bool prepare(Ops& ops,const Packet& p){
  if(prepared||attached||unknown||!valid(p)||p.mode)return false;
  count=p.count;prepared=true;
  for(uint32_t i=0;i<count;++i){
   if(create_owned_text(ops,owners[i],p.units+p.lines[i].text_start,p.lines[i].text_count)!=OwnedTextResult::Ok)return false;
   auto& out=lines[i];const auto& in=p.lines[i];
   out.character=uint8_t(in.character);out.emotion=uint8_t(in.emotion);out.delete_delay=in.delete_delay;out.answer_delay=in.answer_delay;
   out.use_sound_duration=uint8_t(in.flags&1);out.portrait_right=uint8_t((in.flags>>1)&1);out.text=owners[i].value;
   out.wave=in.wave.address;out.sound=in.sound.address;out.table=in.table.address;
  }
  array={reinterpret_cast<uint64_t>(lines),int32_t(count),int32_t(count)};return true;
 }
 bool matches(const TargetStringValue& header)const{return !std::memcmp(&header,&array,sizeof(array));}
 template<class Ops> bool cleanup(Ops& ops){
  if(attached||unknown)return false;
  if(!prepared)return true;
  bool complete=true;
  for(uint32_t i=count;i>0;--i){auto r=release_owned_text(ops,owners[i-1]);if(r==OwnedTextResult::ReleaseDeferred)complete=false;else if(r!=OwnedTextResult::Ok){unknown=true;return false;}}
  if(!complete)return false;
  std::memset(lines,0,sizeof(lines));array={};count=0;prepared=false;return true;
 }
};
}
