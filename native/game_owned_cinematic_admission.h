#pragma once
#include "invocation_protocol.h"

enum class GameOwnedCinematicCall {none,teleport_safe,execute_scavenger};
inline GameOwnedCinematicCall game_owned_cinematic_packet(const CallPacket& packet) {
#ifndef E33_GAME_OWNED_CINEMATIC_SESSION
    (void)packet;return GameOwnedCinematicCall::none;
#else
    if((packet.version!=kCallVersion && packet.version!=kPodCallVersion) || packet.entry_rva!=0x13937a0 ||
       packet.return_offset!=65535 || packet.allocation_extent!=16)return GameOwnedCinematicCall::none;
    if(packet.function_flags==0xc840000 && !packet.parameter_size && !packet.field_count && !packet.object_count)
        return GameOwnedCinematicCall::teleport_safe;
    if(packet.function_flags!=0xc020000 || packet.parameter_size!=8 || packet.field_count!=1 || packet.object_count!=1)
        return GameOwnedCinematicCall::none;
    const auto& field=packet.fields[0];const auto& argument=packet.objects[0];
    if(field.kind!=CallObject || field.offset || field.width!=8 || field.dimension!=1 || field.bool_encoding ||
       field.flags!=0x8001000000294ULL || !field.name[0] || field.name[95] || std::strcmp(field.name,"GameAction") ||
       argument.offset || argument.identity.index<0 || !argument.identity.address)return GameOwnedCinematicCall::none;
    for(unsigned i=0;i<8;++i)if(packet.data[i])return GameOwnedCinematicCall::none;
    return GameOwnedCinematicCall::execute_scavenger;
#endif
}
template<class Ops>
bool admit_game_owned_cinematic(Ops& ops,const CallPacket& packet) {
    const auto kind=game_owned_cinematic_packet(packet);
    if(kind==GameOwnedCinematicCall::none || !ops.live_target() || !ops.exact_function(kind) || !ops.exact_schema(kind))return false;
    return kind==GameOwnedCinematicCall::teleport_safe ||
        (ops.game_action_constraint(packet.fields[0].constraint) && ops.original_scavenger(packet.objects[0].identity));
}
