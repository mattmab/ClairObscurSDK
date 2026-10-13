#pragma once
#include "invocation_protocol.h"
constexpr uint32_t SessionPictoProgression=121;
#pragma pack(push,1)
struct PictoProgressionPacket {
 uint32_t version=1,operation=0,error=0,outcome=0;
 CallIdentity target{},function{},source{},panel{},game_instance{};
 int32_t expected=0,value=0,observed=0; uint32_t reserved=0;
};
#pragma pack(pop)
static_assert(sizeof(PictoProgressionPacket)==112);
inline bool valid_picto_progression(const PictoProgressionPacket& p) {
 if(p.operation==12)return p.version==1 && !p.error && !p.outcome && !p.observed && !p.reserved &&
 p.target.index>=0 && p.target.address && p.function.index>=0 && p.function.address && (p.expected==1 || p.expected==2) &&
 (p.value==1 || p.value==6 || p.value==8 || p.value==9) &&
 !p.source.index && !p.source.serial && !p.source.address && !p.panel.index && !p.panel.serial && !p.panel.address &&
 !p.game_instance.index && !p.game_instance.serial && !p.game_instance.address;
 if(p.operation==11)return p.version==1 && !p.error && !p.outcome && !p.observed && !p.reserved && !p.expected && !p.value &&
 p.target.index>=0 && p.target.address && p.function.index>=0 && p.function.address && p.source.index>=0 && p.source.address &&
 !p.panel.index && !p.panel.serial && !p.panel.address && !p.game_instance.index && !p.game_instance.serial && !p.game_instance.address;
 if(p.operation==10)return p.version==1 && !p.error && !p.outcome && !p.observed && !p.reserved &&
 p.target.index>=0 && p.target.address && p.function.index>=0 && p.function.address &&
 p.source.index>=0 && p.source.address && p.panel.index>=0 && p.panel.address &&
 p.game_instance.index>=0 && p.game_instance.address && p.expected>=0 && p.expected<=1 && p.value>=0 && p.value<=1;
 if(p.operation==9)return p.version==1 && !p.error && !p.outcome && !p.observed && !p.reserved &&
 p.target.index>=0 && p.target.address && p.function.index>=0 && p.function.address && p.expected>=0 &&
 (p.value==1 || p.value==6 || p.value==8 || p.value==9) &&
 !p.source.index && !p.source.serial && !p.source.address && !p.panel.index && !p.panel.serial && !p.panel.address &&
 !p.game_instance.index && !p.game_instance.serial && !p.game_instance.address;
 const auto op=p.operation>=6?3:p.operation>3?p.operation-3:p.operation;
 const bool startup=p.operation>=4 && p.operation<=8;
 const bool panel=startup ? (!p.panel.index && !p.panel.serial && !p.panel.address) : (p.panel.index>=0 && p.panel.address);
 return p.version==1 && p.operation>=1 && p.operation<=8 && !p.error && !p.outcome && !p.observed && !p.reserved && panel &&
 p.target.index>=0 && p.target.address && p.function.index>=0 && p.function.address &&
 (op==1 ? (p.expected>=1 && p.expected<=33 && p.value>=1 && p.value<=33 && p.source.index==0 && !p.source.serial && !p.source.address && !p.game_instance.index && !p.game_instance.serial && !p.game_instance.address) :
 (p.source.index>=0 && p.source.address && p.game_instance.index>=0 && p.game_instance.address && p.expected>=0 && (op==2 || p.expected<=100) && p.value>=0 && p.value<=100));
}
