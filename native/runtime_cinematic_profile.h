// Generated from live runtime-cinematic-feasibility-20261017.json.
// Evidence SHA256: 98afbbf4310c305d4a92113311e617a1d211ff53868b63adaaeb28d2a9efa670
#pragma once
namespace e33_runtime_cinematic {
inline const MeshField demo_fields_0[]={{"ComponentClass","ClassProperty",0,8,7881368067375744ULL,0x6e12ac8ULL,"","",0,"",0U,"ActorComponent"},
{"ReturnValue","ObjectProperty",8,8,6755468161058696ULL,0x6e11d38ULL,"","",0,"",0U,"ActorComponent"}};
inline const MeshField demo_fields_1[]={{"NewMesh","ObjectProperty",0,8,6755468160533120ULL,0x6e11d38ULL,"","",0,"",0U,"SkeletalMesh"}};
inline const MeshField demo_fields_2[]={{"NewAnimToPlay","ObjectProperty",0,8,6755468160533120ULL,0x6e11d38ULL,"","",0,"",0U,"AnimationAsset"},
{"bLooping","BoolProperty",8,1,6755469234274944ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField demo_fields_4[]={{"WorldContextObject","ObjectProperty",0,8,6755468160533122ULL,0x6e11d38ULL,"","",0,"",0U,"Object"},
{"Sound","ObjectProperty",8,8,6755468160533120ULL,0x6e11d38ULL,"","",0,"",0U,"SoundBase"},
{"VolumeMultiplier","FloatProperty",16,4,6759867280786048ULL,0x6e11560ULL,"","",0,"",0U,""},
{"PitchMultiplier","FloatProperty",20,4,6759867280786048ULL,0x6e11560ULL,"","",0,"",0U,""},
{"StartTime","FloatProperty",24,4,6759867280786048ULL,0x6e11560ULL,"","",0,"",0U,""},
{"ConcurrencySettings","ObjectProperty",32,8,6759866207044224ULL,0x6e11d38ULL,"","",0,"",0U,"SoundConcurrency"},
{"bPersistAcrossLevelTransition","BoolProperty",40,1,6759867280786048ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"bAutoDestroy","BoolProperty",41,1,6759867280786048ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"ReturnValue","ObjectProperty",48,8,6755468161058696ULL,0x6e11d38ULL,"","",0,"",0U,"AudioComponent"}};
inline const MeshField demo_fields_5[]={{"StartTime","FloatProperty",0,4,6755469234274944ULL,0x6e11560ULL,"","",0,"",0U,""}};
inline const MeshField demo_fields_7[]={{"Object","ObjectProperty",0,8,6755468160533120ULL,0x6e11d38ULL,"","",0,"",0U,"Object"}};
inline const MeshField demo_fields_8[]={{"bNewLookInput","BoolProperty",0,1,6755469234274944ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField demo_fields_9[]={{"InFieldOfView","FloatProperty",0,4,6755469234274944ULL,0x6e11560ULL,"","",0,"",0U,""}};
inline const MeshField demo_fields_10[]={{"NewLeaderBoneComponent","ObjectProperty",0,8,6755468161057408ULL,0x6e11d38ULL,"","",0,"",0U,"SkinnedMeshComponent"},
{"bForceUpdate","BoolProperty",8,1,6755469234274944ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"bInFollowerShouldTickPose","BoolProperty",9,1,6755469234274944ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField demo_fields_11[]={{"Parent","ObjectProperty",0,8,6755468161057408ULL,0x6e11d38ULL,"","",0,"",0U,"SceneComponent"},
{"SocketName","NameProperty",8,8,6755469234274944ULL,0x6e13040ULL,"","",0,"",0U,""},
{"LocationRule","EnumProperty",16,1,6755469234274944ULL,0x6deeee8ULL,"","ByteProperty",1,"",0U,""},
{"RotationRule","EnumProperty",17,1,6755469234274944ULL,0x6deeee8ULL,"","ByteProperty",1,"",0U,""},
{"ScaleRule","EnumProperty",18,1,6755469234274944ULL,0x6deeee8ULL,"","ByteProperty",1,"",0U,""},
{"bWeldSimulatedBodies","BoolProperty",19,1,6755469234274944ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""},
{"ReturnValue","BoolProperty",20,1,6755469234276224ULL,0x6e119b0ULL,"","",0,"",0xff010001U,""}};
inline const MeshField demo_fields_12[]={{"ReturnValue","IntProperty",0,4,6755469234276224ULL,0x6e10a98ULL,"","",0,"",0U,""}};
inline const MeshField demo_fields_13[]={{"BoneIndex","IntProperty",0,4,6755469234274944ULL,0x6e10a98ULL,"","",0,"",0U,""},
{"ReturnValue","NameProperty",4,8,6755469234276224ULL,0x6e13040ULL,"","",0,"",0U,""}};
inline const MeshFunction demo_functions[]={
{"Actor","GetComponentByClass",1409418243,16,16,8,0x333a230,demo_fields_0,2},
{"SkeletalMeshComponent","SetSkeletalMeshAsset",67240961,8,8,65535,0x36002a0,demo_fields_1,1},
{"SkeletalMeshComponent","PlayAnimation",67240963,9,16,65535,0x35fd9c0,demo_fields_2,2},
{"SkeletalMeshComponent","Stop",67240963,0,0,65535,0x3600a70,nullptr,0},
{"GameplayStatics","CreateSound2D",67249163,56,56,48,0x3736020,demo_fields_4,9},
{"AudioComponent","Play",67240962,4,4,65535,0x353a330,demo_fields_5,1},
{"AudioComponent","Stop",67240962,0,0,65535,0x353c7f0,nullptr,0},
{"ActorComponent","K2_DestroyComponent",67240963,8,8,65535,0x353a100,demo_fields_7,1},
{"Controller","SetIgnoreLookInput",67240962,1,1,65535,0x364e2b0,demo_fields_8,1},
{"CameraComponent","SetFieldOfView",67240960,4,4,65535,0x34cf1b0,demo_fields_9,1},
{"SkinnedMeshComponent","SetLeaderPoseComponent",67240963,10,16,65535,0x32ded00,demo_fields_10,3},
{"SceneComponent","K2_AttachToComponent",67240963,21,24,20,0x32d8610,demo_fields_11,7},
{"SkinnedMeshComponent","GetNumBones",1409418243,4,4,0,0x32dddd0,demo_fields_12,1},
{"SkinnedMeshComponent","GetBoneName",1409418243,12,12,4,0x32dda50,demo_fields_13,2},
};
struct FieldProof {const char* owner; const char* name; const char* type; uint32_t offset,width; uint64_t flags,table; uint32_t boolean;};
inline constexpr FieldProof player_controller={"Player","PlayerController","ObjectProperty",48,8,79938962105311744ULL,0x6e11d38ULL,0U};
inline constexpr FieldProof mesh_skeleton={"SkeletalMesh","Skeleton","ObjectProperty",240,8,79940061617062405ULL,0x6e11d38ULL,0U};
inline constexpr FieldProof animation_skeleton={"AnimationAsset","Skeleton","ObjectProperty",56,8,93450860499173889ULL,0x6e11d38ULL,0U};
inline constexpr FieldProof notifies={"AnimSequenceBase","Notifies","ArrayProperty",128,16,4504149383184896ULL,0x6e0de80ULL,0U};
inline constexpr FieldProof root_motion={"AnimSequence","bEnableRootMotion","BoolProperty",369,1,6756568745902593ULL,0x6e119b0ULL,0xff010001U};
inline constexpr const char* mesh_package="/Game/Characters/Heros/Lune/SK_Lune_Placeholder";
inline constexpr const char* mesh_name="SK_Lune_Placeholder";
inline constexpr const char* animation_package="/Game/Characters/Heros/Lune/Animations/Skills/Lune_Thunder_Kick_IP";
inline constexpr const char* animation_name="Lune_Thunder_Kick_IP";
inline constexpr const char* sound_package="/Game/Audio/WAV/00_Placeholders/UI/Menu/Smart_UI_Interface_Click_An_Ants_Whip_1_Whoosh_Crack_Short_Menu";
inline constexpr const char* sound_name="Smart_UI_Interface_Click_An_Ants_Whip_1_Whoosh_Crack_Short_Menu";
inline constexpr const char* character_packages[]={"/Game/Characters/Heros/Lune/SK_Lune_Placeholder","/Game/MetaHumans/Lune/Face/Lune_FaceMesh","/Game/Characters/Hair/Heroes/Lune/Hair_Lune_2_skl","/Game/Characters/Heros/Maelle/Customization/Skin/SK_Maelle_ActeIII","/Game/MetaHumans/Maelle_v2/Face/Maelle_v2_FaceMesh","/Game/Characters/Hair/Heroes/Maelle/Maelle_Hair_V3_Metahumanskl","/Game/Characters/Enemies/Petank/SK_Petank","/Game/Characters/Heros/Maelle/Sword/SK_Sword_Maelle"};
inline constexpr const char* character_names[]={"SK_Lune_Placeholder","Lune_FaceMesh","Hair_Lune_2_skl","SK_Maelle_ActeIII","Maelle_v2_FaceMesh","Maelle_Hair_V3_Metahumanskl","SK_Petank","SK_Sword_Maelle"};
inline constexpr const char* maelle_animation_package="/Game/Characters/Heros/Maelle/Animations/Skills/Maelle_Skill_DancingFury_B_Inplace";
inline constexpr const char* maelle_animation_name="Maelle_Skill_DancingFury_B_Inplace";
inline constexpr const char* target_animation_package="/Game/Animations/AnimPacks/Idles/MC_Idles_Pack/Shift/Pack_MCIdlesPack_am_Stand_Idle_ShiftL_Loop_01_UE5";
inline constexpr const char* target_animation_name="Pack_MCIdlesPack_am_Stand_Idle_ShiftL_Loop_01_UE5";
}
