#pragma once
struct GpuProperty {const char* name;const char* type;uint32_t offset,width;uint64_t flags,table;uint32_t boolean;};
inline const GpuProperty gpu_properties[]={
{"CaptureComponent2D","ObjectProperty",672,8,0x14c0010000a021dULL,0x6e11d38ULL,0U},
{"FOVAngle","FloatProperty",748,4,0x18001240000205ULL,0x6e11560ULL,0U},
{"TextureTarget","ObjectProperty",768,8,0x11c001000000205ULL,0x6e11d38ULL,0U},
{"bOverride_CustomNearClippingPlane","BoolProperty",2564,1,0x18001000000005ULL,0x6e119b0ULL,0x1010001U},
{"CustomNearClippingPlane","FloatProperty",2568,4,0x18041040000205ULL,0x6e11560ULL,0U},
{"PrimitiveRenderMode","EnumProperty",560,1,0x18001040000205ULL,0x6deeee8ULL,0U},
{"CaptureSource","ByteProperty",561,1,0x18001240000205ULL,0x6e10420ULL,0U},
{"bCaptureEveryFrame","BoolProperty",562,1,0x18001000000005ULL,0x6e119b0ULL,0x1010001U},
{"bCaptureOnMovement","BoolProperty",562,1,0x18001000000005ULL,0x6e119b0ULL,0x2020001U},
{"bUseRayTracingIfEnabled","BoolProperty",644,1,0x18001040000205ULL,0x6e119b0ULL,0xff010001U},
};