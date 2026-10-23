#pragma once
#include "engine_profile_types.h"
// Existing enemy-owner description, shared unchanged with NPC construction.
// This is a profile description, not a second native operation or wire API.
namespace e33_actor_visibility {
inline constexpr MeshField hidden_fields[]={{"bNewHidden","BoolProperty",0,1,6755469234274944ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline constexpr MeshFunction hidden={"Actor","SetActorHiddenInGame",67240962,1,1,65535,0x333fcc0,hidden_fields,1};
}
