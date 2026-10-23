#pragma once
// Exact observed shipping BoxTraceSingle; no reflection codec changes.
namespace e33_volume_query {
inline const MeshField box_fields[]={{"WorldContextObject","ObjectProperty",0,8,0x18001000000282ULL,0x6e11d38ULL,"","",0,"",0U,"Object"},
{"Start","StructProperty",8,24,0x18001040000282ULL,0x6e136a0ULL,"Vector","",0,"",0U,""},
{"End","StructProperty",32,24,0x18001040000282ULL,0x6e136a0ULL,"Vector","",0,"",0U,""},
{"HalfSize","StructProperty",56,24,0x18001040000282ULL,0x6e136a0ULL,"Vector","",0,"",0U,""},
{"Orientation","StructProperty",80,24,0x10001040000282ULL,0x6e136a0ULL,"Rotator","",0,"",0U,""},
{"TraceChannel","ByteProperty",104,1,0x18001040000280ULL,0x6e10420ULL,"","",0,"",0U,""},
{"bTraceComplex","BoolProperty",105,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"ActorsToIgnore","ArrayProperty",112,16,0x10000008000382ULL,0x6e0de80ULL,"","ObjectProperty",8,"",0U,""},
{"DrawDebugType","ByteProperty",128,1,0x18001040000280ULL,0x6e10420ULL,"","",0,"",0U,""},
{"OutHit","StructProperty",136,248,0x10009040000180ULL,0x6e136a0ULL,"HitResult","",0,"",0U,""},
{"bIgnoreSelf","BoolProperty",384,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"TraceColor","StructProperty",388,16,0x18041040000280ULL,0x6e136a0ULL,"LinearColor","",0,"",0U,""},
{"TraceHitColor","StructProperty",404,16,0x18041040000280ULL,0x6e136a0ULL,"LinearColor","",0,"",0U,""},
{"DrawTime","FloatProperty",420,4,0x18041040000280ULL,0x6e11560ULL,"","",0,"",0U,""},
{"ReturnValue","BoolProperty",424,1,0x18001040000780ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshFunction box_profile={"KismetSystemLibrary","BoxTraceSingle",79832067,425,432,424,0x382d110,box_fields,15};
}
