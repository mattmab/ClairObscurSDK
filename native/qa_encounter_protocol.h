#pragma once
#include "invocation_protocol.h"
constexpr uint32_t SessionQAEncounter=134;
#pragma pack(push,1)
struct QAEncounterPacket {
 uint32_t version,operation,error,outcome;
 CallIdentity world,enemy,component,gi,function;
 uint32_t removed,reserved;
};
#pragma pack(pop)
static_assert(sizeof(QAEncounterPacket)==104);
