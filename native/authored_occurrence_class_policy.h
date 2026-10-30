#pragma once
#include <cstdint>

// Exact supported sequence layouts, selected by stable native class identity.
// The adapter separately validates the actual MovieScene field, value and
// reciprocal owner; this policy alone never admits a binding or dispatch.
namespace e33_authored_occurrence {
template<class Ops> bool movie_scene_layout(Ops& ops,uint64_t type,uint64_t& owner,uint32_t& offset) {
    owner=0;offset=0;
    if(!ops.class_valid(type))return false;
    if(ops.named(type,"LevelSequence","/Script/LevelSequence")) {owner=type;offset=112;return true;}
    uint64_t base=type;
    if(ops.named(type,"CameraAnimationSequence","/Script/TemplateSequence")) {
        if(ops.size(type)!=232)return false;
        base=ops.super(type);
    }
    if(!ops.class_valid(base) || !ops.named(base,"TemplateSequence","/Script/TemplateSequence") || ops.size(base)!=232)return false;
    const auto parent=ops.super(base);
    if(!ops.class_valid(parent) || !ops.named(parent,"MovieSceneSequence","/Script/MovieScene") || ops.size(parent)!=104)return false;
    owner=base;offset=104;return true;
}
}
