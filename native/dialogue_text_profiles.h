#pragma once
// Exact parameter metadata captured from the running original dialogue system.
namespace e33_dialogue_text {
struct Parameter {const char* name;const char* type;int32_t offset,width;uint64_t flags;const char* related;};
inline constexpr Parameter parameters_0[]={
{"Dialog","ObjectProperty",0,8,2251868533162644ULL,"BP_Dialogue_C"},
{"Lines","ArrayProperty",8,16,134218132ULL,"TextProperty"},
{"Character","ObjectProperty",24,8,2251868533162644ULL,"BP_DataAsset_DialogueCharacter_C"},
};
inline constexpr Parameter parameters_1[]={
{"Dialogue","ObjectProperty",0,8,2251868533162644ULL,"BP_Dialogue_C"},
{"Choices","ArrayProperty",8,16,134218132ULL,"TextProperty"},
{"CameraType","ByteProperty",24,1,2251869606904468ULL,"EDialogueCameraType"},
{"CustomOptions","StructProperty",32,72,2252349569499284ULL,"S_Dialogue_CustomOptions"},
};
inline constexpr Parameter parameters_2[]={
{"Dialog","ObjectProperty",0,8,2251868533162644ULL,"BP_Dialogue_C"},
{"Parameters","StructProperty",8,2,2251869606903956ULL,"S_Dialogue_EndParameters"},
};
}
