#pragma once
#include "invocation_protocol.h"
namespace e33_retired_world {
enum class OwningPlayerResult {Valid,Null,Invalid};
// reflected_call scrubs UObject pointer bytes and captures exact observations
// in the output slot list. Never interpret the zeroed parameter bytes as null.
inline OwningPlayerResult owning_player_output(const CallPacket&packet,CallIdentity&out){
 out={};
 if(packet.outcome!=CallDispatchReturned)return OwningPlayerResult::Invalid;
 if(packet.object_count==0)return OwningPlayerResult::Null;
 if(packet.object_count!=1||packet.objects[0].offset!=0)return OwningPlayerResult::Invalid;
 const auto id=packet.objects[0].identity;
 if(id.index<0||id.serial<=0||!id.address)return OwningPlayerResult::Invalid;
 for(unsigned i=0;i<8;++i)if(packet.data[i])return OwningPlayerResult::Invalid;
 out=id;return OwningPlayerResult::Valid;
}
}
