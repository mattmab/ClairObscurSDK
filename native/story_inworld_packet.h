#pragma once
#include "invocation_protocol.h"
#include "owned_text_value.h"
#include <initializer_list>
namespace e33_story_inworld {
constexpr uint32_t operation=235,capacity=16,units_capacity=8192,rejected=3930,uncertain=3931,pending=3932;
#pragma pack(push,1)
struct InputLine {
 uint32_t character=0,emotion=0,flags=0,text_start=0,text_count=0,reserved=0;
 double delete_delay=0,answer_delay=0;
 CallIdentity wave{},sound{},table{};char row[96]{};
};
struct Packet {
 uint32_t version=3,op=operation,error=0,state=0;uint64_t owner=0,ticket=0,asset_lease=0,system_lease=0;
 CallIdentity carrier{},asset{},system{},play{},query{},interrupt{},finished{},widget_interrupt{};
 uint32_t mode=0,count=0,used_units=0,reserved=0;
 InputLine lines[capacity]{};uint16_t units[units_capacity]{};uint8_t tail[1464]{};
};
#pragma pack(pop)
static_assert(sizeof(InputLine)==184,"In-world input line");
static_assert(sizeof(Packet)==20984,"In-world packet");
inline bool identity(const CallIdentity& id){return id.index>=0&&id.serial>0&&id.address>=0x10000&&id.address<=0x7fffffffffffULL&&!(id.address&7);}
inline bool zero_identity(const CallIdentity& id){return !id.index&&!id.serial&&!id.address;}
inline bool valid(const Packet& p){
 if(p.version!=3||p.op!=operation||p.error||p.state||!p.owner||!p.ticket||!p.asset_lease||!p.system_lease||p.mode>4||p.reserved||
    !identity(p.carrier)||!identity(p.asset)||!identity(p.system)||!identity(p.play)||!identity(p.query)||!identity(p.interrupt)||!identity(p.finished)||!identity(p.widget_interrupt)||
    p.count>capacity||p.used_units>units_capacity||(p.mode==0?(!p.count||!p.used_units):(p.count||p.used_units)))return false;
 uint32_t end=0;
 for(uint32_t i=0;i<capacity;++i){
  const auto& l=p.lines[i];
  if(i>=p.count){InputLine zero{};if(std::memcmp(&l,&zero,sizeof(l)))return false;continue;}
  // First qualified profile covers the source Gustave and Sophie portraits.
  if((l.character!=0&&l.character!=9)||l.emotion||l.flags>3||l.reserved||
     !std::isfinite(l.delete_delay)||!std::isfinite(l.answer_delay)||l.delete_delay<0||l.delete_delay>120||l.answer_delay<0||l.answer_delay>120||
     l.text_start!=end||l.text_count>p.used_units-end||!valid_text_units(p.units+end,l.text_count))return false;
  for(const auto& id:{l.wave,l.sound,l.table})if(!zero_identity(id)&&!identity(id))return false;
  bool nul=false;for(char c:l.row){if(!c)nul=true;else if(nul||static_cast<unsigned char>(c)<32||static_cast<unsigned char>(c)>126)return false;}
  if(!nul)return false;
  end+=l.text_count;
 }
 if(end!=p.used_units)return false;
 for(uint32_t i=end;i<units_capacity;++i)if(p.units[i])return false;
 for(auto c:p.tail)if(c)return false;
 return true;
}
}
