#pragma once
// Fixed native adapter contracts from the live effects report.
namespace e33_runtime_cinematic {
inline const MeshField fx_fields_0[]={{"WorldContextObject","ObjectProperty",0,8,6755468160533122ULL,0x6e11d38ULL,"","",0,"",0U,"Object"},
{"SystemTemplate","ObjectProperty",8,8,6755468160533120ULL,0x6e11d38ULL,"","",0,"",0U,""},
{"Location","StructProperty",16,24,6755469234274944ULL,0x6e136a0ULL,"Vector","",0,"",0U,""},
{"Rotation","StructProperty",40,24,4503669420589696ULL,0x6e136a0ULL,"Rotator","",0,"",0U,""},
{"Scale","StructProperty",64,24,6755469234274944ULL,0x6e136a0ULL,"Vector","",0,"",0U,""},
{"bAutoDestroy","BoolProperty",88,1,6755469234274944ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"bAutoActivate","BoolProperty",89,1,6755469234274944ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"PoolingMethod","EnumProperty",90,1,6755469234274944ULL,0x6deeee8ULL,"","ByteProperty",1,"",0U,""},
{"bPreCullCheck","BoolProperty",91,1,6755469234274944ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"ReturnValue","ObjectProperty",96,8,6755468161058696ULL,0x6e11d38ULL,"","",0,"",0U,""}};
inline const MeshFunction fx_functions[]={
{"NiagaraFunctionLibrary","SpawnSystemAtLocation",75637763,104,104,96,0x4472b70,fx_fields_0,10},
};
}
