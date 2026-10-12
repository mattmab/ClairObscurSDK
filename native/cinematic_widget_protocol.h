#pragma once
#include "invocation_protocol.h"
constexpr uint32_t SessionCinematicWidget=119;
enum WidgetResource { WidgetGetter,WidgetNativeGetter,WidgetLibrary,WidgetComponent,
    WidgetGraph,WidgetTrackClass,WidgetUserClass,WidgetRegister,WidgetUnregister,
    WidgetControls,WidgetRemove,WidgetResourceCount };
#pragma pack(push,1)
struct CinematicWidgetPacket {
    uint32_t version,operation;
    uint64_t owner,reserved;
    uint32_t error,state,observed,failed;
    CallIdentity resources[WidgetResourceCount],player;
    uint64_t tokens[WidgetResourceCount];
    CallPacket remove;
};
#pragma pack(pop)
static_assert(sizeof(CinematicWidgetPacket)==40+16*(WidgetResourceCount+1)+8*WidgetResourceCount+sizeof(CallPacket));
