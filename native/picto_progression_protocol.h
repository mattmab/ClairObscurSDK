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
 return p.version==1 && (p.operation==1 || p.operation==2 || p.operation==3) && !p.error && !p.outcome && !p.observed && !p.reserved &&
 p.target.index>=0 && p.target.address && p.function.index>=0 && p.function.address && p.panel.index>=0 && p.panel.address &&
 (p.operation==1 ? (p.expected>=1 && p.expected<=33 && p.value>=1 && p.value<=33 && p.source.index==0 && !p.source.serial && !p.source.address && !p.game_instance.index && !p.game_instance.serial && !p.game_instance.address) :
 (p.source.index>=0 && p.source.address && p.game_instance.index>=0 && p.game_instance.address && p.expected>=0 && (p.operation==2 || p.expected<=100) && p.value>=0 && p.value<=100));
}
