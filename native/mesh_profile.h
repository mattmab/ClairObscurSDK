// Generated from the exact shipping-build observations in dist/mesh-feasibility.
#pragma once
#include "engine_profiles.h"
inline const MeshField mesh_fields_0[]={{"WorldContextObject","ObjectProperty",0,8,0x18001000000282ULL,0x6e11d38ULL,"","",0,"",0U,"Object"},
{"ActorClass","ClassProperty",8,8,0x1c001000000280ULL,0x6e12ac8ULL,"","",0,"",0U,"Actor"},
{"SpawnTransform","StructProperty",16,96,0x18001048000182ULL,0x6e136a0ULL,"Transform","",0,"",0U,""},
{"CollisionHandlingOverride","EnumProperty",112,1,0x18001040000280ULL,0x6deeee8ULL,"","ByteProperty",1,"",0U,""},
{"Owner","ObjectProperty",120,8,0x18001000000280ULL,0x6e11d38ULL,"","",0,"",0U,"Actor"},
{"TransformScaleMethod","EnumProperty",128,1,0x18001040000280ULL,0x6deeee8ULL,"","ByteProperty",1,"",0U,""},
{"ReturnValue","ObjectProperty",136,8,0x18001000000780ULL,0x6e11d38ULL,"","",0,"",0U,"Actor"}};
inline const MeshField mesh_fields_1[]={{"Actor","ObjectProperty",0,8,0x18001000000280ULL,0x6e11d38ULL,"","",0,"",0U,"Actor"},
{"SpawnTransform","StructProperty",16,96,0x18001048000182ULL,0x6e136a0ULL,"Transform","",0,"",0U,""},
{"TransformScaleMethod","EnumProperty",112,1,0x18001040000280ULL,0x6deeee8ULL,"","ByteProperty",1,"",0U,""},
{"ReturnValue","ObjectProperty",120,8,0x18001000000780ULL,0x6e11d38ULL,"","",0,"",0U,"Actor"}};
inline const MeshField mesh_fields_2[]={{"Class","ClassProperty",0,8,0x1c001000000280ULL,0x6e12ac8ULL,"","",0,"",0U,"ActorComponent"},
{"bManualAttachment","BoolProperty",8,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"RelativeTransform","StructProperty",16,96,0x18001048000182ULL,0x6e136a0ULL,"Transform","",0,"",0U,""},
{"bDeferredFinish","BoolProperty",112,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"ReturnValue","ObjectProperty",120,8,0x18001000080788ULL,0x6e11d38ULL,"","",0,"",0U,"ActorComponent"}};
inline const MeshField mesh_fields_3[]={{"Component","ObjectProperty",0,8,0x18001000080280ULL,0x6e11d38ULL,"","",0,"",0U,"ActorComponent"},
{"bManualAttachment","BoolProperty",8,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"RelativeTransform","StructProperty",16,96,0x18001048000182ULL,0x6e136a0ULL,"Transform","",0,"",0U,""}};
inline const MeshField mesh_fields_4[]={{"SectionIndex","IntProperty",0,4,0x18001040000280ULL,0x6e10a98ULL,"","",0,"",0U,""},
{"Vertices","ArrayProperty",8,16,0x10000008000382ULL,0x6e0de80ULL,"","StructProperty",24,"Vector",0U,""},
{"Triangles","ArrayProperty",24,16,0x10000008000382ULL,0x6e0de80ULL,"","IntProperty",4,"",0U,""},
{"Normals","ArrayProperty",40,16,0x10000008000382ULL,0x6e0de80ULL,"","StructProperty",24,"Vector",0U,""},
{"UV0","ArrayProperty",56,16,0x10000008000382ULL,0x6e0de80ULL,"","StructProperty",16,"Vector2D",0U,""},
{"UV1","ArrayProperty",72,16,0x10040008000382ULL,0x6e0de80ULL,"","StructProperty",16,"Vector2D",0U,""},
{"UV2","ArrayProperty",88,16,0x10040008000382ULL,0x6e0de80ULL,"","StructProperty",16,"Vector2D",0U,""},
{"UV3","ArrayProperty",104,16,0x10040008000382ULL,0x6e0de80ULL,"","StructProperty",16,"Vector2D",0U,""},
{"VertexColors","ArrayProperty",120,16,0x10000008000382ULL,0x6e0de80ULL,"","StructProperty",16,"LinearColor",0U,""},
{"Tangents","ArrayProperty",136,16,0x10000008000382ULL,0x6e0de80ULL,"","StructProperty",32,"ProcMeshTangent",0U,""},
{"bCreateCollision","BoolProperty",152,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"bSRGBConversion","BoolProperty",153,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField mesh_fields_6[]={{"ReturnValue","StructProperty",0,24,0x18001040000780ULL,0x6e136a0ULL,"Vector","",0,"",0U,""}};
inline const MeshField mesh_fields_7[]={{"ReturnValue","StructProperty",0,24,0x18001040000780ULL,0x6e136a0ULL,"Vector","",0,"",0U,""}};
inline const MeshField mesh_fields_8[]={{"bNewActorEnableCollision","BoolProperty",0,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField mesh_fields_9[]={{"NewMobility","ByteProperty",0,1,0x18001040000280ULL,0x6e10420ULL,"","",0,"",0U,""}};
inline const MeshField mesh_fields_10[]={{"ReturnValue","IntProperty",0,4,0x18001040000780ULL,0x6e10a98ULL,"","",0,"",0U,""}};
inline const MeshField mesh_fields_11[]={{"ReturnValue","BoolProperty",0,1,0x18001040000780ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField mesh_fields_12[]={{"ElementIndex","IntProperty",0,4,0x18001040000280ULL,0x6e10a98ULL,"","",0,"",0U,""},
{"SourceMaterial","ObjectProperty",8,8,0x18001000000280ULL,0x6e11d38ULL,"","",0,"",0U,"MaterialInterface"},
{"OptionalName","NameProperty",16,8,0x18001040000280ULL,0x6e13040ULL,"","",0,"",0U,""},
{"ReturnValue","ObjectProperty",24,8,0x18001000000780ULL,0x6e11d38ULL,"","",0,"",0U,"MaterialInstanceDynamic"}};
inline const MeshField mesh_fields_13[]={{"ParameterName","NameProperty",0,8,0x18001040000280ULL,0x6e13040ULL,"","",0,"",0U,""},
{"Value","ObjectProperty",8,8,0x18001000000280ULL,0x6e11d38ULL,"","",0,"",0U,"Texture"}};
inline const MeshField mesh_fields_14[]={{"ParameterName","NameProperty",0,8,0x18001040000280ULL,0x6e13040ULL,"","",0,"",0U,""},
{"ReturnValue","ObjectProperty",8,8,0x18001000000780ULL,0x6e11d38ULL,"","",0,"",0U,"Texture"}};
inline const MeshField mesh_fields_15[]={{"InString","StrProperty",0,16,0x18000000000280ULL,0x6e131d8ULL,"","",0,"",0U,""},
{"ReturnValue","NameProperty",16,8,0x18001040000780ULL,0x6e13040ULL,"","",0,"",0U,""}};
inline const MeshField mesh_fields_16[]={{"WorldContextObject","ObjectProperty",0,8,0x18001000000280ULL,0x6e11d38ULL,"","",0,"",0U,"Object"},
{"Filename","StrProperty",8,16,0x18000000000280ULL,0x6e131d8ULL,"","",0,"",0U,""},
{"ReturnValue","ObjectProperty",24,8,0x18001000000780ULL,0x6e11d38ULL,"","",0,"",0U,"Texture2D"}};
inline const MeshField mesh_fields_17[]={{"WorldContextObject","ObjectProperty",0,8,0x18001000000282ULL,0x6e11d38ULL,"","",0,"",0U,"Object"},
{"Start","StructProperty",8,24,0x18001040000282ULL,0x6e136a0ULL,"Vector","",0,"",0U,""},
{"End","StructProperty",32,24,0x18001040000282ULL,0x6e136a0ULL,"Vector","",0,"",0U,""},
{"TraceChannel","ByteProperty",56,1,0x18001040000280ULL,0x6e10420ULL,"","",0,"",0U,""},
{"bTraceComplex","BoolProperty",57,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"ActorsToIgnore","ArrayProperty",64,16,0x10000008000382ULL,0x6e0de80ULL,"","ObjectProperty",8,"",0U,""},
{"DrawDebugType","ByteProperty",80,1,0x18001040000280ULL,0x6e10420ULL,"","",0,"",0U,""},
{"OutHit","StructProperty",88,248,0x10009040000180ULL,0x6e136a0ULL,"HitResult","",0,"",0U,""},
{"bIgnoreSelf","BoolProperty",336,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"TraceColor","StructProperty",340,16,0x18041040000280ULL,0x6e136a0ULL,"LinearColor","",0,"",0U,""},
{"TraceHitColor","StructProperty",356,16,0x18041040000280ULL,0x6e136a0ULL,"LinearColor","",0,"",0U,""},
{"DrawTime","FloatProperty",372,4,0x18041040000280ULL,0x6e11560ULL,"","",0,"",0U,""},
{"ReturnValue","BoolProperty",376,1,0x18001040000780ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField mesh_fields_18[]={{"Hit","StructProperty",0,248,0x10009048000182ULL,0x6e136a0ULL,"HitResult","",0,"",0U,""},
{"bBlockingHit","BoolProperty",248,1,0x18001040000380ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"bInitialOverlap","BoolProperty",249,1,0x18001040000380ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"Time","FloatProperty",252,4,0x18041040000380ULL,0x6e11560ULL,"","",0,"",0U,""},
{"Distance","FloatProperty",256,4,0x18041040000380ULL,0x6e11560ULL,"","",0,"",0U,""},
{"Location","StructProperty",264,24,0x18041040000380ULL,0x6e136a0ULL,"Vector","",0,"",0U,""},
{"ImpactPoint","StructProperty",288,24,0x18041040000380ULL,0x6e136a0ULL,"Vector","",0,"",0U,""},
{"Normal","StructProperty",312,24,0x18041040000380ULL,0x6e136a0ULL,"Vector","",0,"",0U,""},
{"ImpactNormal","StructProperty",336,24,0x18041040000380ULL,0x6e136a0ULL,"Vector","",0,"",0U,""},
{"PhysMat","ObjectProperty",360,8,0x18041000000380ULL,0x6e11d38ULL,"","",0,"",0U,"PhysicalMaterial"},
{"HitActor","ObjectProperty",368,8,0x18041000000380ULL,0x6e11d38ULL,"","",0,"",0U,"Actor"},
{"HitComponent","ObjectProperty",376,8,0x18041000080380ULL,0x6e11d38ULL,"","",0,"",0U,"PrimitiveComponent"},
{"HitBoneName","NameProperty",384,8,0x18041040000380ULL,0x6e13040ULL,"","",0,"",0U,""},
{"BoneName","NameProperty",392,8,0x18041040000380ULL,0x6e13040ULL,"","",0,"",0U,""},
{"HitItem","IntProperty",400,4,0x18041040000380ULL,0x6e10a98ULL,"","",0,"",0U,""},
{"ElementIndex","IntProperty",404,4,0x18041040000380ULL,0x6e10a98ULL,"","",0,"",0U,""},
{"FaceIndex","IntProperty",408,4,0x18041040000380ULL,0x6e10a98ULL,"","",0,"",0U,""},
{"TraceStart","StructProperty",416,24,0x18041040000380ULL,0x6e136a0ULL,"Vector","",0,"",0U,""},
{"TraceEnd","StructProperty",440,24,0x18041040000380ULL,0x6e136a0ULL,"Vector","",0,"",0U,""}};
inline const MeshField mesh_fields_19[]={{"ParameterName","NameProperty",0,8,0x18001040000280ULL,0x6e13040ULL,"","",0,"",0U,""},
{"Value","StructProperty",8,16,0x18001040000280ULL,0x6e136a0ULL,"LinearColor","",0,"",0U,""}};
inline const MeshField mesh_fields_20[]={{"ReturnValue","IntProperty",0,4,0x18001040000780ULL,0x6e10a98ULL,"","",0,"",0U,""}};
inline const MeshField mesh_fields_21[]={{"BoneIndex","IntProperty",0,4,0x18001040000280ULL,0x6e10a98ULL,"","",0,"",0U,""},
{"ReturnValue","NameProperty",4,8,0x18001040000780ULL,0x6e13040ULL,"","",0,"",0U,""}};
inline const MeshField mesh_fields_22[]={{"BoneIndex","IntProperty",0,4,0x18001040000280ULL,0x6e10a98ULL,"","",0,"",0U,""},
{"ReturnValue","StructProperty",16,96,0x18001040000580ULL,0x6e136a0ULL,"Transform","",0,"",0U,""}};
inline const MeshField mesh_fields_23[]={{"InBoneName","NameProperty",0,8,0x18001040000280ULL,0x6e13040ULL,"","",0,"",0U,""},
{"TransformSpace","ByteProperty",8,1,0x18001040000280ULL,0x6e10420ULL,"","",0,"",0U,""},
{"ReturnValue","StructProperty",16,96,0x18001040000580ULL,0x6e136a0ULL,"Transform","",0,"",0U,""}};
inline const MeshField mesh_fields_24[]={{"BoneName","NameProperty",0,8,0x18001040000280ULL,0x6e13040ULL,"","",0,"",0U,""},
{"ReturnValue","NameProperty",8,8,0x18001040000780ULL,0x6e13040ULL,"","",0,"",0U,""}};
inline const MeshField mesh_fields_25[]={{"SectionIndex","IntProperty",0,4,0x18001040000280ULL,0x6e10a98ULL,"","",0,"",0U,""},
{"Vertices","ArrayProperty",8,16,0x10000008000382ULL,0x6e0de80ULL,"","StructProperty",24,"Vector",0U,""},
{"Normals","ArrayProperty",24,16,0x10000008000382ULL,0x6e0de80ULL,"","StructProperty",24,"Vector",0U,""},
{"UV0","ArrayProperty",40,16,0x10000008000382ULL,0x6e0de80ULL,"","StructProperty",16,"Vector2D",0U,""},
{"UV1","ArrayProperty",56,16,0x10040008000382ULL,0x6e0de80ULL,"","StructProperty",16,"Vector2D",0U,""},
{"UV2","ArrayProperty",72,16,0x10040008000382ULL,0x6e0de80ULL,"","StructProperty",16,"Vector2D",0U,""},
{"UV3","ArrayProperty",88,16,0x10040008000382ULL,0x6e0de80ULL,"","StructProperty",16,"Vector2D",0U,""},
{"VertexColors","ArrayProperty",104,16,0x10000008000382ULL,0x6e0de80ULL,"","StructProperty",16,"LinearColor",0U,""},
{"Tangents","ArrayProperty",120,16,0x10000008000382ULL,0x6e0de80ULL,"","StructProperty",32,"ProcMeshTangent",0U,""},
{"bSRGBConversion","BoolProperty",136,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField mesh_fields_26[]={{"NewHidden","BoolProperty",0,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"bPropagateToChildren","BoolProperty",1,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField mesh_fields_27[]={{"ReturnValue","BoolProperty",0,1,0x18001040000780ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField mesh_fields_28[]={{"ReturnValue","ObjectProperty",0,8,0x18001000000780ULL,0x6e11d38ULL,"","",0,"",0U,"Actor"}};
inline const MeshField mesh_fields_29[]={{"BoneName","NameProperty",0,8,0x18001040000280ULL,0x6e13040ULL,"","",0,"",0U,""},
{"ReturnValue","IntProperty",8,4,0x18001040000780ULL,0x6e10a98ULL,"","",0,"",0U,""}};
inline const MeshField hair_location_fields[]={{"NewLocation","StructProperty",0,24,0x18001040000280ULL,0x6e136a0ULL,"Vector","",0,"",0U,""},{"bSweep","BoolProperty",24,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},{"SweepHitResult","StructProperty",32,248,0x10009040000180ULL,0x6e136a0ULL,"HitResult","",0,"",0U,""},{"bTeleport","BoolProperty",280,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField hair_transform_fields_0[]={{"NewTransform","StructProperty",0,96,0x18001048000182ULL,0x6e136a0ULL,"Transform","",0,"",0U,""},{"bSweep","BoolProperty",96,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},{"SweepHitResult","StructProperty",104,248,0x10009040000180ULL,0x6e136a0ULL,"HitResult","",0,"",0U,""},{"bTeleport","BoolProperty",352,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField hair_transform_fields_1[]={{"ReturnValue","StructProperty",0,96,0x18001040000580ULL,0x6e136a0ULL,"Transform","",0,"",0U,""}};
inline const MeshField hair_world_fields_0[]={{"ReturnValue","StructProperty",0,96,0x18001040000580ULL,0x6e136a0ULL,"Transform","",0,"",0U,""}};
inline const MeshField hair_world_fields_1[]={{"NewTransform","StructProperty",0,96,0x18001048000182ULL,0x6e136a0ULL,"Transform","",0,"",0U,""},{"bSweep","BoolProperty",96,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},{"SweepHitResult","StructProperty",104,248,0x10009040000180ULL,0x6e136a0ULL,"HitResult","",0,"",0U,""},{"bTeleport","BoolProperty",352,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField hair_world_fields_2[]={{"bNewAbsoluteLocation","BoolProperty",0,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},{"bNewAbsoluteRotation","BoolProperty",1,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},{"bNewAbsoluteScale","BoolProperty",2,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshFunction mesh_functions[]={
e33_engine_profiles::profiles[0],
e33_engine_profiles::profiles[1],
{"Actor","AddComponentByClass",0x4c20403,128,128,120,0x3338bf0,mesh_fields_2,5},
{"Actor","FinishAddComponent",0x4c20403,112,112,65535,0x3339610,mesh_fields_3,3},
{"ProceduralMeshComponent","CreateMeshSection_LinearColor",0x4420401,154,160,65535,0x5ab6e30,mesh_fields_4,12},
e33_engine_profiles::profiles[2],
e33_engine_profiles::profiles[3],
{"Actor","GetActorForwardVector",0x54820403,24,24,0,0x3339b80,mesh_fields_7,1},
e33_engine_profiles::profiles[47],
e33_engine_profiles::profiles[16],
{"ProceduralMeshComponent","GetNumSections",0x54020401,4,4,0,0x5ab75d0,mesh_fields_10,1},
{"Actor","IsActorBeingDestroyed",0x54020401,1,1,0,0x333be80,mesh_fields_11,1},
{"PrimitiveComponent","CreateDynamicMaterialInstance",0x4020402,32,32,24,0x32c71f0,mesh_fields_12,4},
{"MaterialInstanceDynamic","SetTextureParameterValue",0x4020403,16,16,65535,0x391f420,mesh_fields_13,2},
{"MaterialInstanceDynamic","K2_GetTextureParameterValue",0x4020403,16,16,8,0x391e550,mesh_fields_14,2},
{"KismetStringLibrary","Conv_StringToName",0x14022403,24,24,16,0x383b800,mesh_fields_15,2},
e33_engine_profiles::profiles[51],
e33_engine_profiles::profiles[14],
e33_engine_profiles::profiles[15],
{"MaterialInstanceDynamic","SetVectorParameterValue",0x4820403,24,24,65535,0x391f980,mesh_fields_19,2},
{"SkinnedMeshComponent","GetNumBones",0x54020403,4,4,0,0x32dddd0,mesh_fields_20,1},
{"SkinnedMeshComponent","GetBoneName",0x54020403,12,12,4,0x32dda50,mesh_fields_21,2},
{"SkinnedMeshComponent","GetRefPoseTransform",0x54820403,112,112,16,0x32ddf90,mesh_fields_22,2},
{"SkinnedMeshComponent","GetBoneTransform",0x54820401,112,112,16,0x32ddae0,mesh_fields_23,3},
{"SkinnedMeshComponent","GetParentBone",0x54020403,16,16,8,0x32dde30,mesh_fields_24,2},
{"ProceduralMeshComponent","UpdateMeshSection_LinearColor",0x4420401,137,144,65535,0x5ab8450,mesh_fields_25,10},
{"SceneComponent","SetHiddenInGame",0x4020401,2,2,65535,0x32d9f50,mesh_fields_26,2},
{"Pawn","IsPlayerControlled",0x54020402,1,1,0,0x3a9c1a0,mesh_fields_27,1},
e33_engine_profiles::profiles[18],
{"SkinnedMeshComponent","GetBoneIndex",0x54020403,12,12,8,0x32dd9b0,mesh_fields_29,2},
{"SceneComponent","K2_SetRelativeLocation",0x4c20403,281,288,65535,0x32d8a90,hair_location_fields,4},
{"SceneComponent","K2_SetRelativeTransform",0x4c20403,353,368,65535,0x32d90b0,hair_transform_fields_0,4},
{"SceneComponent","GetRelativeTransform",0x54820403,96,96,0,0x32d6c70,hair_transform_fields_1,1},
e33_engine_profiles::profiles[19],
e33_engine_profiles::profiles[20],
{"SceneComponent","SetAbsolute",0x4020403,3,3,65535,0x32d9e20,hair_world_fields_2,3},
};
inline const MeshField mesh_Transform[]={{"Rotation","StructProperty",0,32,0x18001041000005ULL,0x6e136a0ULL,"Quat","",0,"",0U,""},
{"Translation","StructProperty",32,24,0x18001041000205ULL,0x6e136a0ULL,"Vector","",0,"",0U,""},
{"Scale3D","StructProperty",64,24,0x18001041000205ULL,0x6e136a0ULL,"Vector","",0,"",0U,""}};
inline const MeshField mesh_Quat[]={{"X","DoubleProperty",0,8,0x18001041000205ULL,0x6e11788ULL,"","",0,"",0U,""},
{"Y","DoubleProperty",8,8,0x18001041000205ULL,0x6e11788ULL,"","",0,"",0U,""},
{"Z","DoubleProperty",16,8,0x18001041000205ULL,0x6e11788ULL,"","",0,"",0U,""},
{"W","DoubleProperty",24,8,0x18001041000205ULL,0x6e11788ULL,"","",0,"",0U,""}};
