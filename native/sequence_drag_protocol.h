#pragma once
#include "invocation_protocol.h"
#include <algorithm>
#pragma pack(push,1)
struct SequenceDragConfig {
    uint32_t magic,version;
    CallIdentity seek,pause;
    int32_t start,end;
    uint32_t reserved[4];
};
struct SequenceDragStatus {
    uint32_t magic,version,counter,dragging;
    int32_t frame;float subframe;
    double value;
    uint32_t reserved[8];
};
#pragma pack(pop)
static_assert(sizeof(SequenceDragConfig)==64 && sizeof(SequenceDragStatus)==64);

inline bool sequence_drag_position(const SequenceDragConfig& config,float value,int32_t& frame,float& subframe){
    if(config.end<=config.start || !std::isfinite(value) || value<0 || value>1)return false;
    if(value==1.f){frame=config.end-1;subframe=0;return true;}
    const double cursor=config.start+double(value)*(int64_t(config.end)-config.start);
    const auto whole=static_cast<int64_t>(std::floor(cursor));
    frame=static_cast<int32_t>(whole);subframe=static_cast<float>(cursor-whole);
    if(subframe>=1.f){if(frame==config.end-1)subframe=std::nextafter(1.f,0.f);else{++frame;subframe=0;}}
    return frame>=config.start && frame<config.end;
}

#pragma pack(push,1)
struct SequenceViewportStatus {
    uint32_t magic,version,revision,pick_counter;
    double start,end,pick_frame;
    uint32_t lane,reserved[5];
};
#pragma pack(pop)
static_assert(sizeof(SequenceViewportStatus)==64);
inline bool sequence_viewport_zoom(double full_start,double full_end,double anchor,double steps,bool pan,double& start,double& end){
    if(!std::isfinite(anchor) || !std::isfinite(steps) || !std::isfinite(start) || !std::isfinite(end) ||
       full_end<=full_start || start<full_start || end>full_end || end<=start)return false;
    anchor=std::clamp(anchor,0.,1.);steps=std::clamp(steps,-12.,12.);
    const double span=end-start,whole=full_end-full_start;
    if(pan){const auto shift=-steps*span*.15;start+=shift;end+=shift;}
    else{
        const double point=start+anchor*span;
        const double size=std::clamp(span*std::pow(1.35,-steps),std::min(1.,whole),whole);
        start=point-anchor*size;end=start+size;
    }
    if(start<full_start){end+=full_start-start;start=full_start;}
    if(end>full_end){start-=end-full_end;end=full_end;}
    return true;
}

inline int sequence_timeline_lane(double y){
    if(!std::isfinite(y) || y<.75 || y>=.925)return -1;
    return std::min(6,static_cast<int>((y-.75)/.025));
}
inline bool sequence_timeline_ruler(double y){return std::isfinite(y) && y>=.93 && y<=.95;}
