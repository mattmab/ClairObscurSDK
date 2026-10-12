#pragma once
// Derived from evidence/sequence-support-schema.json; no stock layouts.
struct SequenceSettingField { const char* name; const char* type; uint32_t offset,width; uint64_t flags,table; uint32_t boolean; const char* nested; };
inline constexpr SequenceSettingField fields_MovieSceneSequenceLoopCount[]={
    {"Value","IntProperty",0,4,6755469234274821ULL,0x6e10a98,0,""},
};
inline constexpr SequenceSettingField fields_MovieSceneSequenceTickInterval[]={
    {"TickIntervalSeconds","FloatProperty",0,4,6755469234274817ULL,0x6e11560,0,""},
    {"EvaluationBudgetMicroseconds","FloatProperty",4,4,6755469234274817ULL,0x6e11560,0,""},
    {"bTickWhenPaused","BoolProperty",8,1,6755469234274817ULL,0x6e119b0,0xff010001,""},
    {"bAllowRounding","BoolProperty",9,1,6755469234274817ULL,0x6e119b0,0xff010001,""},
};
inline constexpr SequenceSettingField fields_MovieSceneSequencePlaybackSettings[]={
    {"bAutoPlay","BoolProperty",0,1,6755468160532485ULL,0x6e119b0,0x1010001,""},
    {"LoopCount","StructProperty",4,4,4503668346847237ULL,0x6e136a0,0,"MovieSceneSequenceLoopCount"},
    {"TickInterval","StructProperty",8,12,4503668346847233ULL,0x6e136a0,0,"MovieSceneSequenceTickInterval"},
    {"PlayRate","FloatProperty",20,4,6755469234274821ULL,0x6e11560,0,""},
    {"StartTime","FloatProperty",24,4,6755469234274821ULL,0x6e11560,0,""},
    {"bRandomStartTime","BoolProperty",28,1,6755468160532485ULL,0x6e119b0,0x1010001,""},
    {"bDisableMovementInput","BoolProperty",28,1,6755468160532485ULL,0x6e119b0,0x2020001,""},
    {"bDisableLookAtInput","BoolProperty",28,1,6755468160532485ULL,0x6e119b0,0x4040001,""},
    {"bHidePlayer","BoolProperty",28,1,6755468160532485ULL,0x6e119b0,0x8080001,""},
    {"bHideHud","BoolProperty",28,1,6755468160532485ULL,0x6e119b0,0x10100001,""},
    {"bDisableCameraCuts","BoolProperty",28,1,6755468160532485ULL,0x6e119b0,0x20200001,""},
    {"FinishCompletionStateOverride","EnumProperty",32,1,6755469234274821ULL,0x6deeee8,0,"EMovieSceneCompletionModeOverride"},
    {"bPauseAtEnd","BoolProperty",36,1,6755468160532485ULL,0x6e119b0,0x1010001,""},
    {"bInheritTickIntervalFromOwner","BoolProperty",36,1,6755468160532481ULL,0x6e119b0,0x2020001,""},
    {"bDynamicWeighting","BoolProperty",36,1,6755468160532481ULL,0x6e119b0,0x4040001,""},
};
