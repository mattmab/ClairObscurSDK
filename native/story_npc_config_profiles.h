#pragma once
#include "engine_profile_types.h"
namespace e33_story_npc {
inline const MeshField fields_0[]={
{"Object","ObjectProperty",0,8,6755468160533120ULL,0x6e11d38ULL,"","",0,"",0U,"Object"},
{"PropertyName","NameProperty",8,8,6755469234274944ULL,0x6e13040ULL,"","",0,"",0U,""},
{"Value","ClassProperty",16,8,7881368067375744ULL,0x6e12ac8ULL,"","",0,"",0U,"Object"},
};
inline const MeshField fields_1[]={
{"Object","ObjectProperty",0,8,6755468160533120ULL,0x6e11d38ULL,"","",0,"",0U,"Object"},
{"PropertyName","NameProperty",8,8,6755469234274944ULL,0x6e13040ULL,"","",0,"",0U,""},
{"Value","ObjectProperty",16,8,6755468160533120ULL,0x6e11d38ULL,"","",0,"",0U,"Object"},
};
inline const MeshField fields_2[]={
{"Object","ObjectProperty",0,8,6755468160533120ULL,0x6e11d38ULL,"","",0,"",0U,"Object"},
{"PropertyName","NameProperty",8,8,6755469234274944ULL,0x6e13040ULL,"","",0,"",0U,""},
{"Value","BoolProperty",16,1,6755469234274944ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
};
inline const MeshField fields_3[]={
{"bNewActorEnableCollision","BoolProperty",0,1,6755469234274944ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
};
inline const MeshFunction functions[]={
{"KismetSystemLibrary","SetClassPropertyByName",67249155,24,24,65535,0x387afa0ULL,fields_0,3},
{"KismetSystemLibrary","SetObjectPropertyByName",67249155,24,24,65535,0x387caa0ULL,fields_1,3},
{"KismetSystemLibrary","SetBoolPropertyByName",67249155,17,24,65535,0x387aae0ULL,fields_2,3},
{"Actor","SetActorEnableCollision",67240963,1,1,65535,0x333fc30ULL,fields_3,1},
};
}
