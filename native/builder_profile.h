#pragma once
namespace e33_builder {
using namespace e33_mesh;
inline const MeshField fields_0[]={{"WorldContextObject","ObjectProperty",0,8,0x18001000000282ULL,0x6e11d38ULL,"","",0,"",0U,"Object"},
{"ActorClass","ClassProperty",8,8,0x1c001000000280ULL,0x6e12ac8ULL,"","",0,"",0U,"Actor"},
{"SpawnTransform","StructProperty",16,96,0x18001048000182ULL,0x6e136a0ULL,"Transform","",0,"",0U,""},
{"CollisionHandlingOverride","EnumProperty",112,1,0x18001040000280ULL,0x6deeee8ULL,"","ByteProperty",1,"",0U,""},
{"Owner","ObjectProperty",120,8,0x18001000000280ULL,0x6e11d38ULL,"","",0,"",0U,"Actor"},
{"TransformScaleMethod","EnumProperty",128,1,0x18001040000280ULL,0x6deeee8ULL,"","ByteProperty",1,"",0U,""},
{"ReturnValue","ObjectProperty",136,8,0x18001000000780ULL,0x6e11d38ULL,"","",0,"",0U,"Actor"}};
inline const MeshField fields_1[]={{"Actor","ObjectProperty",0,8,0x18001000000280ULL,0x6e11d38ULL,"","",0,"",0U,"Actor"},
{"SpawnTransform","StructProperty",16,96,0x18001048000182ULL,0x6e136a0ULL,"Transform","",0,"",0U,""},
{"TransformScaleMethod","EnumProperty",112,1,0x18001040000280ULL,0x6deeee8ULL,"","ByteProperty",1,"",0U,""},
{"ReturnValue","ObjectProperty",120,8,0x18001000000780ULL,0x6e11d38ULL,"","",0,"",0U,"Actor"}};
inline const MeshField fields_3[]={{"ReturnValue","StructProperty",0,24,0x18001040000780ULL,0x6e136a0ULL,"Vector","",0,"",0U,""}};
inline const MeshField fields_4[]={{"ReturnValue","StructProperty",0,24,0x10001040000780ULL,0x6e136a0ULL,"Rotator","",0,"",0U,""}};
inline const MeshField fields_5[]={{"NewLocation","StructProperty",0,24,0x18001040000280ULL,0x6e136a0ULL,"Vector","",0,"",0U,""},
{"NewRotation","StructProperty",24,24,0x10001040000280ULL,0x6e136a0ULL,"Rotator","",0,"",0U,""},
{"bSweep","BoolProperty",48,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"SweepHitResult","StructProperty",56,248,0x10009040000180ULL,0x6e136a0ULL,"HitResult","",0,"",0U,""},
{"bTeleport","BoolProperty",304,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"ReturnValue","BoolProperty",305,1,0x18001040000780ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField fields_6[]={{"NewViewTarget","ObjectProperty",0,8,0x18001000000280ULL,0x6e11d38ULL,"","",0,"",0U,"Actor"},
{"BlendTime","FloatProperty",8,4,0x18001040000280ULL,0x6e11560ULL,"","",0,"",0U,""},
{"blendFunc","ByteProperty",12,1,0x18001040000280ULL,0x6e10420ULL,"","",0,"",0U,""},
{"BlendExp","FloatProperty",16,4,0x18001040000280ULL,0x6e11560ULL,"","",0,"",0U,""},
{"bLockOutgoing","BoolProperty",20,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField fields_7[]={{"ReturnValue","ObjectProperty",0,8,0x18001000000780ULL,0x6e11d38ULL,"","",0,"",0U,"Actor"}};
inline const MeshField fields_8[]={{"ReturnValue","StructProperty",0,24,0x10001040000780ULL,0x6e136a0ULL,"Rotator","",0,"",0U,""}};
inline const MeshField fields_9[]={{"bNewMoveInput","BoolProperty",0,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField fields_10[]={{"NewMovementMode","ByteProperty",0,1,0x18001040000280ULL,0x6e10420ULL,"","",0,"",0U,""},
{"NewCustomMode","ByteProperty",1,1,0x18001040000280ULL,0x6e10420ULL,"","",0,"",0U,""}};
inline const MeshField fields_11[]={{"ReturnValue","BoolProperty",0,1,0x18001040000780ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField fields_12[]={{"ReturnValue","StructProperty",0,24,0x18001040000780ULL,0x6e136a0ULL,"Vector","",0,"",0U,""}};
inline const MeshField fields_13[]={{"ReturnValue","StructProperty",0,24,0x10001040000780ULL,0x6e136a0ULL,"Rotator","",0,"",0U,""}};
inline const MeshField fields_14[]={{"WorldContextObject","ObjectProperty",0,8,0x18001000000282ULL,0x6e11d38ULL,"","",0,"",0U,"Object"},
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
inline const MeshField fields_15[]={{"Hit","StructProperty",0,248,0x10009048000182ULL,0x6e136a0ULL,"HitResult","",0,"",0U,""},
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
inline const MeshField fields_16[]={{"NewMobility","ByteProperty",0,1,0x18001040000280ULL,0x6e10420ULL,"","",0,"",0U,""}};
inline const MeshField fields_17[]={{"ReturnValue","ObjectProperty",0,8,0x18001000080788ULL,0x6e11d38ULL,"","",0,"",0U,"SceneComponent"}};
inline const MeshField fields_18[]={{"ReturnValue","ObjectProperty",0,8,0x18001000000780ULL,0x6e11d38ULL,"","",0,"",0U,"Actor"}};
inline const MeshField fields_19[]={{"ReturnValue","StructProperty",0,96,0x18001040000580ULL,0x6e136a0ULL,"Transform","",0,"",0U,""}};
inline const MeshField fields_20[]={{"NewTransform","StructProperty",0,96,0x18001048000182ULL,0x6e136a0ULL,"Transform","",0,"",0U,""},
{"bSweep","BoolProperty",96,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"SweepHitResult","StructProperty",104,248,0x10009040000180ULL,0x6e136a0ULL,"HitResult","",0,"",0U,""},
{"bTeleport","BoolProperty",352,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField fields_21[]={{"ReturnValue","ObjectProperty",0,8,0x18001000000780ULL,0x6e11d38ULL,"","",0,"",0U,"Pawn"}};
inline const MeshField fields_22[]={{"ReturnValue","BoolProperty",0,1,0x18001040000780ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField fields_23[]={{"NewRotation","StructProperty",0,24,0x10001048000382ULL,0x6e136a0ULL,"Rotator","",0,"",0U,""}};
inline const MeshField fields_24[]={{"WorldLocation","StructProperty",0,24,0x18001040000280ULL,0x6e136a0ULL,"Vector","",0,"",0U,""},
{"ScreenLocation","StructProperty",24,16,0x18001040000380ULL,0x6e136a0ULL,"Vector2D","",0,"",0U,""},
{"bPlayerViewportRelative","BoolProperty",40,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"ReturnValue","BoolProperty",41,1,0x18001040000780ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField fields_25[]={{"bOnlyCollidingComponents","BoolProperty",0,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"Origin","StructProperty",8,24,0x18001040000380ULL,0x6e136a0ULL,"Vector","",0,"",0U,""},
{"BoxExtent","StructProperty",32,24,0x18001040000380ULL,0x6e136a0ULL,"Vector","",0,"",0U,""},
{"bIncludeFromChildActors","BoolProperty",56,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField fields_26[]={{"InPosition","StructProperty",0,16,0x18001040000280ULL,0x6e136a0ULL,"Vector2D","",0,"",0U,""}};
inline const MeshField fields_27[]={{"InSize","StructProperty",0,16,0x18001040000280ULL,0x6e136a0ULL,"Vector2D","",0,"",0U,""}};
inline const MeshField fields_28[]={{"InVisibility","EnumProperty",0,1,0x18001040000280ULL,0x6deeee8ULL,"","ByteProperty",1,"",0U,""}};
inline const MeshField fields_29[]={{"InText","TextProperty",0,16,0x10000000000080ULL,0x6e1ba00ULL,"","",0,"",0U,""}};
inline const MeshField fields_31[]={{"WorldContextObject","ObjectProperty",0,8,0x18001000000282ULL,0x6e11d38ULL,"","",0,"",0U,"Object"},
{"ReturnValue","FloatProperty",8,4,0x18001040000780ULL,0x6e11560ULL,"","",0,"",0U,""}};
inline const MeshField fields_32[]={{"SizeX","IntProperty",0,4,0x18001040000380ULL,0x6e10a98ULL,"","",0,"",0U,""},
{"SizeY","IntProperty",4,4,0x18001040000380ULL,0x6e10a98ULL,"","",0,"",0U,""}};
inline const MeshField fields_33[]={{"InBrushColor","StructProperty",0,16,0x18001040000280ULL,0x6e136a0ULL,"LinearColor","",0,"",0U,""}};
inline const MeshField fields_34[]={{"WorldContextObject","ObjectProperty",0,8,0x18001000000282ULL,0x6e11d38ULL,"","",0,"",0U,"Object"},
{"ReturnValue","BoolProperty",8,1,0x18001040000780ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField fields_35[]={{"ElementIndex","IntProperty",0,4,0x18001040000280ULL,0x6e10a98ULL,"","",0,"",0U,""},
{"Material","ObjectProperty",8,8,0x18001000000280ULL,0x6e11d38ULL,"","",0,"",0U,"MaterialInterface"}};
inline const MeshField fields_36[]={{"ElementIndex","IntProperty",0,4,0x18001040000280ULL,0x6e10a98ULL,"","",0,"",0U,""},
{"ReturnValue","ObjectProperty",8,8,0x18001000000780ULL,0x6e11d38ULL,"","",0,"",0U,"MaterialInterface"}};
inline const MeshField fields_37[]={{"min","StructProperty",0,24,0x18001040000380ULL,0x6e136a0ULL,"Vector","",0,"",0U,""},
{"max","StructProperty",24,24,0x18001040000380ULL,0x6e136a0ULL,"Vector","",0,"",0U,""}};
inline const MeshField fields_38[]={{"ReturnValue","IntProperty",0,4,0x18001040000780ULL,0x6e10a98ULL,"","",0,"",0U,""}};
inline const MeshField fields_39[]={{"ReturnValue","BoolProperty",0,1,0x18001040000780ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField fields_40[]={{"ScreenX","FloatProperty",0,4,0x18001040000280ULL,0x6e11560ULL,"","",0,"",0U,""},
{"ScreenY","FloatProperty",4,4,0x18001040000280ULL,0x6e11560ULL,"","",0,"",0U,""},
{"WorldLocation","StructProperty",8,24,0x18001040000380ULL,0x6e136a0ULL,"Vector","",0,"",0U,""},
{"WorldDirection","StructProperty",32,24,0x18001040000380ULL,0x6e136a0ULL,"Vector","",0,"",0U,""},
{"ReturnValue","BoolProperty",56,1,0x18001040000780ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField fields_42[]={{"InComponent","ObjectProperty",0,8,0x18001000080280ULL,0x6e11d38ULL,"","",0,"",0U,"PrimitiveComponent"}};
inline const MeshField fields_44[]={{"WorldContextObject","ObjectProperty",0,8,0x18001000000280ULL,0x6e11d38ULL,"","",0,"",0U,"Object"},
{"Width","IntProperty",8,4,0x18001040000280ULL,0x6e10a98ULL,"","",0,"",0U,""},
{"Height","IntProperty",12,4,0x18001040000280ULL,0x6e10a98ULL,"","",0,"",0U,""},
{"Format","ByteProperty",16,1,0x18001040000280ULL,0x6e10420ULL,"","",0,"",0U,""},
{"ClearColor","StructProperty",20,16,0x18001040000280ULL,0x6e136a0ULL,"LinearColor","",0,"",0U,""},
{"bAutoGenerateMipMaps","BoolProperty",36,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"bSupportUAVs","BoolProperty",37,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"ReturnValue","ObjectProperty",40,8,0x18001000000780ULL,0x6e11d38ULL,"","",0,"",0U,"TextureRenderTarget2D"}};
inline const MeshField fields_45[]={{"TextureRenderTarget","ObjectProperty",0,8,0x18001000000280ULL,0x6e11d38ULL,"","",0,"",0U,"TextureRenderTarget2D"}};
inline const MeshField fields_46[]={{"NewMesh","ObjectProperty",0,8,0x18001000000280ULL,0x6e11d38ULL,"","",0,"",0U,"StaticMesh"},
{"ReturnValue","BoolProperty",8,1,0x18001040000780ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField fields_47[]={{"bNewActorEnableCollision","BoolProperty",0,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField fields_48[]={{"bValue","BoolProperty",0,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField fields_49[]={{"InActor","ObjectProperty",0,8,0x18001000000280ULL,0x6e11d38ULL,"","",0,"",0U,"Actor"},
{"bIncludeFromChildActors","BoolProperty",8,1,0x18001040000282ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField fields_50[]={{"WorldContextObject","ObjectProperty",0,8,0x18001000000280ULL,0x6e11d38ULL,"","",0,"",0U,"Object"},
{"TextureRenderTarget","ObjectProperty",8,8,0x18001000000280ULL,0x6e11d38ULL,"","",0,"",0U,"TextureRenderTarget2D"},
{"FilePath","StrProperty",16,16,0x18000000000280ULL,0x6e131d8ULL,"","",0,"",0U,""},
{"Filename","StrProperty",32,16,0x18000000000280ULL,0x6e131d8ULL,"","",0,"",0U,""}};
inline const MeshField fields_51[]={{"WorldContextObject","ObjectProperty",0,8,0x18001000000280ULL,0x6e11d38ULL,"","",0,"",0U,"Object"},
{"Filename","StrProperty",8,16,0x18000000000280ULL,0x6e131d8ULL,"","",0,"",0U,""},
{"ReturnValue","ObjectProperty",24,8,0x18001000000780ULL,0x6e11d38ULL,"","",0,"",0U,"Texture2D"}};
inline const MeshField fields_52[]={{"bChannel0","BoolProperty",0,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"bChannel1","BoolProperty",1,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"bChannel2","BoolProperty",2,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField fields_53[]={{"bChannel0","BoolProperty",0,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"bChannel1","BoolProperty",1,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"bChannel2","BoolProperty",2,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField fields_54[]={{"NewIntensity","FloatProperty",0,4,0x18001040000280ULL,0x6e11560ULL,"","",0,"",0U,""}};
inline const MeshField fields_55[]={{"NewLightColor","StructProperty",0,16,0x18001040000280ULL,0x6e136a0ULL,"LinearColor","",0,"",0U,""},
{"bSRGB","BoolProperty",16,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField fields_56[]={{"NewRadius","FloatProperty",0,4,0x18001040000280ULL,0x6e11560ULL,"","",0,"",0U,""}};
inline const MeshField fields_57[]={{"bNewValue","BoolProperty",0,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField fields_58[]={{"bEnabled","BoolProperty",0,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField fields_59[]={{"bSimulate","BoolProperty",0,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField fields_60[]={{"NewCastShadow","BoolProperty",0,1,0x18001040000280ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField rotator_fields[]={{"Pitch","DoubleProperty",0,8,0x18001041000205ULL,0x6e11788ULL,"","",0,"",0U,""},
{"Yaw","DoubleProperty",8,8,0x18001041000205ULL,0x6e11788ULL,"","",0,"",0U,""},
{"Roll","DoubleProperty",16,8,0x18001041000205ULL,0x6e11788ULL,"","",0,"",0U,""}};
inline const MeshFunction profiles[]={
{"GameplayStatics","BeginDeferredActorSpawnFromClass",0x4c22403,144,144,136,0x37336c0,fields_0,7},
{"GameplayStatics","FinishSpawningActor",0x4c22403,128,128,120,0x37372f0,fields_1,4},
{"Actor","K2_DestroyActor",0x4020402,0,0,65535,0x333dcd0,nullptr,0},
{"Actor","K2_GetActorLocation",0x54820403,24,24,0,0x333de20,fields_3,1},
{"Actor","K2_GetActorRotation",0x54820403,24,24,0,0x333dea0,fields_4,1},
{"Actor","K2_SetActorLocationAndRotation",0x4c20403,306,312,305,0x333e530,fields_5,6},
{"PlayerController","SetViewTargetWithBlend",0x4020402,21,24,65535,0x3b2c940,fields_6,5},
{"Controller","GetViewTarget",0x54020402,8,8,0,0x364baa0,fields_7,1},
{"Controller","GetControlRotation",0x54820402,24,24,0,0x36447a0,fields_8,1},
{"Controller","SetIgnoreMoveInput",0x4020402,1,1,65535,0x364e340,fields_9,1},
{"CharacterMovementComponent","SetMovementMode",0x4020402,2,2,65535,0x3571b70,fields_10,2},
{"Pawn","IsLocallyControlled",0x54020402,1,1,0,0x3a9c0e0,fields_11,1},
{"PlayerCameraManager","GetCameraLocation",0x54820402,24,24,0,0x32c77c0,fields_12,1},
{"PlayerCameraManager","GetCameraRotation",0x54820402,24,24,0,0x32c7810,fields_13,1},
{"KismetSystemLibrary","LineTraceSingle",0x4c22403,377,384,376,0x385db00,fields_14,13},
{"GameplayStatics","BreakHitResult",0x14c22403,464,464,65535,0x3734ed0,fields_15,19},
{"SceneComponent","SetMobility",0x4020402,1,1,65535,0x32da020,fields_16,1},
{"Actor","K2_GetRootComponent",0x54020403,8,8,0,0x333e1a0,fields_17,1},
{"ActorComponent","GetOwner",0x54020403,8,8,0,0x3539df0,fields_18,1},
{"SceneComponent","K2_GetComponentToWorld",0x54820403,96,96,0,0x32d8a00,fields_19,1},
{"SceneComponent","K2_SetWorldTransform",0x4c20403,353,368,65535,0x32d9930,fields_20,4},
{"Controller","K2_GetPawn",0x54020403,8,8,0,0x321c2e0,fields_21,1},
{"Controller","IsMoveInputIgnored",0x54020402,1,1,0,0x364c340,fields_22,1},
{"Controller","SetControlRotation",0x4c20402,24,24,65535,0x364d0a0,fields_23,1},
{"PlayerController","ProjectWorldLocationToScreen",0x54c20403,42,48,41,0x3b27f10,fields_24,4},
{"Actor","GetActorBounds",0x54c20402,57,64,65535,0x33398d0,fields_25,4},
{"CanvasPanelSlot","SetPosition",0x4820403,16,16,65535,0x30976a0,fields_26,1},
{"CanvasPanelSlot","SetSize",0x4820403,16,16,65535,0x3097cf0,fields_27,1},
{"Widget","SetVisibility",0x4020402,1,1,65535,0x310ca20,fields_28,1},
{"TextBlock","SetText",0x4020402,16,16,65535,0x310b570,fields_29,1},
{"Widget","RemoveFromParent",0x4020402,0,0,65535,0x31018d0,nullptr,0},
{"WidgetLayoutLibrary","GetViewportScale",0x1402240b,12,16,8,0x313ab50,fields_31,2},
{"PlayerController","GetViewportSize",0x54420403,8,8,65535,0x3b26b70,fields_32,2},
{"Border","SetBrushColor",0x4820403,16,16,65535,0x30961e0,fields_33,1},
{"GameplayStatics","IsGamePaused",0x14022403,9,16,8,0x373c130,fields_34,2},
{"PrimitiveComponent","SetMaterial",0x4020402,16,16,65535,0x32cd4c0,fields_35,2},
{"PrimitiveComponent","GetMaterial",0x54020402,16,16,8,0x32c8380,fields_36,2},
{"StaticMeshComponent","GetLocalBounds",0x54c20403,48,48,65535,0x3646360,fields_37,2},
{"PrimitiveComponent","GetNumMaterials",0x54020402,4,4,0,0x32c87c0,fields_38,1},
{"SceneComponent","IsVisible",0x54020402,1,1,0,0x32d71c0,fields_39,1},
{"PlayerController","DeprojectScreenPositionToWorld",0x54c20403,57,64,56,0x3b23d30,fields_40,5},
{"SceneCaptureComponent2D","CaptureScene",0x4020403,0,0,65535,0x32d6720,nullptr,0},
{"SceneCaptureComponent","ShowOnlyComponent",0x4020403,8,8,65535,0x36008d0,fields_42,1},
{"SceneCaptureComponent","ClearShowOnlyComponents",0x4020403,0,0,65535,0x35faba0,nullptr,0},
{"KismetRenderingLibrary","CreateRenderTarget2D",0x4822403,48,48,40,0x383f2c0,fields_44,8},
{"KismetRenderingLibrary","ReleaseRenderTarget2D",0x4022403,8,8,65535,0x3877270,fields_45,1},
{"StaticMeshComponent","SetStaticMesh",0x4020402,9,16,8,0x3651070,fields_46,2},
{"Actor","SetActorEnableCollision",0x4020403,1,1,65535,0x333fc30,fields_47,1},
{"PrimitiveComponent","SetVisibleInSceneCaptureOnly",0x4020403,1,1,65535,0x32cea70,fields_48,1},
{"SceneCaptureComponent","ShowOnlyActorComponents",0x4020403,9,16,65535,0x3600600,fields_49,2},
{"KismetRenderingLibrary","ExportRenderTarget",0x4022403,48,48,65535,0x3847ee0,fields_50,4},
{"KismetRenderingLibrary","ImportFileAsTexture2D",0x4022403,32,32,24,0x3854c30,fields_51,3},
{"PrimitiveComponent","SetLightingChannels",0x4020403,3,3,65535,0x32cd000,fields_52,3},
{"LightComponent","SetLightingChannels",0x4020403,3,3,65535,0x35b8f10,fields_53,3},
{"LightComponent","SetIntensity",0x4020403,4,4,65535,0x35b83a0,fields_54,1},
{"LightComponent","SetLightColor",0x4820403,17,20,65535,0x35b8660,fields_55,2},
{"LocalLightComponent","SetAttenuationRadius",0x4020403,4,4,65535,0x35b6200,fields_56,1},
{"PointLightComponent","SetUseInverseSquaredFalloff",0x4020403,1,1,65535,0x35ba630,fields_57,1},
{"Actor","SetActorTickEnabled",0x4020402,1,1,65535,0x333fe80,fields_58,1},
{"PrimitiveComponent","SetSimulatePhysics",0x4020402,1,1,65535,0x32ce3e0,fields_59,1},
{"PrimitiveComponent","SetCastShadow",0x4020403,1,1,65535,0x32cbbe0,fields_60,1},
};
inline const char* packages[]={"/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/UMG","/Script/UMG","/Script/UMG","/Script/UMG","/Script/UMG","/Script/UMG","/Script/Engine","/Script/UMG","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine","/Script/Engine"};
}