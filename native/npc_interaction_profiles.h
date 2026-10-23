#pragma once
// Exact observed shipping profiles; no dynamic schema or codec extension.
namespace e33_npc_interaction {
inline const MeshField SetCollisionEnabled_fields[]={
{"NewType","ByteProperty",0,1,0x18001040000280ULL,0x6e10420ULL,"","",0,"",0U,""},
};
inline const MeshFunction SetCollisionEnabled={"PrimitiveComponent","SetCollisionEnabled",0x4020402,1,1,65535,0x32cbd50,SetCollisionEnabled_fields,1};
inline const MeshField GetCollisionEnabled_fields[]={
{"ReturnValue","ByteProperty",0,1,0x18001040000780ULL,0x6e10420ULL,"","",0,"",0U,""},
};
inline const MeshFunction GetCollisionEnabled={"PrimitiveComponent","GetCollisionEnabled",0x54020402,1,1,0,0x32c7b40,GetCollisionEnabled_fields,1};
inline const MeshField SetCollisionResponseToChannel_fields[]={
{"Channel","ByteProperty",0,1,0x18001040000280ULL,0x6e10420ULL,"","",0,"",0U,""},
{"NewResponse","ByteProperty",1,1,0x18001040000280ULL,0x6e10420ULL,"","",0,"",0U,""},
};
inline const MeshFunction SetCollisionResponseToChannel={"PrimitiveComponent","SetCollisionResponseToChannel",0x4020402,2,2,65535,0x32cbfa0,SetCollisionResponseToChannel_fields,2};
inline const MeshField GetCollisionResponseToChannel_fields[]={
{"Channel","ByteProperty",0,1,0x18001040000280ULL,0x6e10420ULL,"","",0,"",0U,""},
{"ReturnValue","ByteProperty",1,1,0x18001040000780ULL,0x6e10420ULL,"","",0,"",0U,""},
};
inline const MeshFunction GetCollisionResponseToChannel={"PrimitiveComponent","GetCollisionResponseToChannel",0x54020402,2,2,1,0x32c7be0,GetCollisionResponseToChannel_fields,2};
inline const MeshField K2_SphereOverlapComponent_fields[]={
{"InSphereCentre","StructProperty",0,24,0x18001040000280ULL,0x6e136a0ULL,"Vector","",0,"",0U,""},
{"InSphereRadius","FloatProperty",24,4,0x18001040000280ULL,0x6e11560ULL,"","",0,"",0U,""},
{"bTraceComplex","BoolProperty",28,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"bShowTrace","BoolProperty",29,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"bPersistentShowTrace","BoolProperty",30,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"HitLocation","StructProperty",32,24,0x18001040000380ULL,0x6e136a0ULL,"Vector","",0,"",0U,""},
{"HitNormal","StructProperty",56,24,0x18001040000380ULL,0x6e136a0ULL,"Vector","",0,"",0U,""},
{"BoneName","NameProperty",80,8,0x18001040000380ULL,0x6e13040ULL,"","",0,"",0U,""},
{"OutHit","StructProperty",88,248,0x10009040000180ULL,0x6e136a0ULL,"HitResult","",0,"",0U,""},
{"ReturnValue","BoolProperty",336,1,0x18001040000780ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
};
inline const MeshFunction K2_SphereOverlapComponent={"PrimitiveComponent","K2_SphereOverlapComponent",0x4c20403,337,344,336,0x32ca5f0,K2_SphereOverlapComponent_fields,10};
}
