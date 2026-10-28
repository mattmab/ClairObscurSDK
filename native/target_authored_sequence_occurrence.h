#pragma once
#include "authored_sequence_occurrence.h"
#include "target_authored_binding_query.h"
#include "authored_occurrence_class_policy.h"
#include <array>

// Research-only exact-build reader for the sequence references used by the
// Scene Editor. The enclosing native owner must retain/revalidate its root and
// source and call on the game thread. This does not authorize dispatch or take
// leases; the research-gated authored-binding diagnostic owns those duties.
struct TargetAuthoredOccurrenceNative {
    static bool is_class(uint64_t base,uint64_t object) {return call_is_class(base,object);}
    static CallIdentity capture(uint64_t base,uint64_t object) {return call_capture(base,object);}
};

template<class QueryOps, class Native=TargetAuthoredOccurrenceNative> struct TargetAuthoredOccurrenceReader {
    using Identity=CallIdentity;
    QueryOps& ops;
    uint32_t failure=0;
    bool reject(uint32_t stage) {failure=stage;return false;}
    bool context()const{return ops.context();}
    bool valid(const Identity& value)const{return ops.valid(value);}
    bool same(const Identity& a,const Identity& b)const{return ops.same(a,b);}
    bool class_valid(uint64_t type)const{return type && Native::is_class(ops.base,type);}
    bool named(uint64_t type,const char* name,const char* package)const{return ops.named(type,name,package);}
    uint64_t super(uint64_t type)const{return local_read<uint64_t>(type+0x40);}
    uint32_t size(uint64_t type)const{return local_read<uint32_t>(type+0x58);}
    bool valid_hierarchy(uint64_t type)const {
        if(!type)return false;
        for(unsigned i=0;i<32;++i) {
            if(!type)return true;
            if(!Native::is_class(ops.base,type))return false;
            type=local_read<uint64_t>(type+0x40);
        }
        return false;
    }
    uint64_t ancestor(uint64_t type,const char* name,const char* package)const {
        for(unsigned i=0;type && i<32;++i,type=local_read<uint64_t>(type+0x40)) {
            if(!Native::is_class(ops.base,type))return 0;
            if(ops.named(type,name,package))return type;
        }
        return 0;
    }
    bool object_array_schema(uint64_t owner,const char* name,uint32_t offset,uint64_t flags,
                             const char* type,const char* package)const {
        const auto array=ops.field(owner,name,offset,16,0x6e0de80,flags);
        if(!array || (local_read<uint8_t>(array+0x70)&1))return false;
        const auto inner=local_read<uint64_t>(array+0x78);
        return inner && local_read<uint64_t>(inner)==ops.base+0x6e11d38 &&
            local_read<uint64_t>(inner+0x10)==array && local_read<uint32_t>(inner+0x30)==1 &&
            local_read<uint32_t>(inner+0x34)==8 && !local_read<uint32_t>(inner+0x44) &&
            ops.named(local_read<uint64_t>(inner+0x70),type,package);
    }
    static bool array_header(const e33_camera_binding::ObjectArray& h,uint32_t width,uint32_t limit) {
        return h.count>=0 && h.capacity>=h.count && static_cast<uint32_t>(h.count)<=limit && h.capacity<=4096 &&
            (!h.capacity ? !h.data : h.data && !(h.data&7)) &&
            h.data<=UINT64_MAX-uint64_t(h.capacity)*width;
    }
    template<class Sink> bool pointer_array(uint64_t address,Sink sink)const {
        const auto h=local_read<e33_camera_binding::ObjectArray>(address);
        if(!array_header(h,8,512))return false;
        std::array<uint64_t,512> values{};
        for(int32_t i=0;i<h.count;++i) {
            values[i]=local_read<uint64_t>(h.data+uint64_t(i)*8);
            if(!values[i])return false;
            // Repeating the same pointer inside a single array is ambiguous:
            // do not silently collapse a possible additional occurrence. This
            // is deliberately local to the array; e.g. CameraCutTrack may
            // refer to a track already seen through a separate track array.
            for(int32_t j=0;j<i;++j)if(values[j]==values[i])return false;
            if(!sink(values[i]))return false;
        }
        const auto after=local_read<e33_camera_binding::ObjectArray>(address);
        if(std::memcmp(&h,&after,sizeof(h)))return false;
        for(int32_t i=0;i<h.count;++i)if(values[i]!=local_read<uint64_t>(h.data+uint64_t(i)*8))return false;
        return context();
    }
    template<class Sink> bool children(const Identity& sequence,Sink sink) {
        if(!context() || !valid(sequence))return reject(1);
        const auto type=local_read<uint64_t>(sequence.address+16);
        uint64_t movie_owner=0;uint32_t movie_offset=0;
        if(!e33_authored_occurrence::movie_scene_layout(*this,type,movie_owner,movie_offset))return reject(2);
        const auto movie=ops.field(movie_owner,"MovieScene",movie_offset,8,0x6e11d38,79938962105827848ULL);
        if(!movie || !ops.named(local_read<uint64_t>(movie+0x70),"MovieScene","/Script/MovieScene"))return reject(3);
        const auto scene=Native::capture(ops.base,local_read<uint64_t>(sequence.address+movie_offset));
        if(!valid(scene) || local_read<uint64_t>(scene.address+16)!=local_read<uint64_t>(movie+0x70) ||
           local_read<uint64_t>(scene.address+32)!=sequence.address)return reject(4);
        const auto scene_class=local_read<uint64_t>(scene.address+16);
        if(!object_array_schema(scene_class,"Tracks",224,91198442210066952ULL,"MovieSceneTrack","/Script/MovieScene"))return reject(5);
        const auto bindings=ops.field(scene_class,"ObjectBindings",128,16,0x6e0de80,18014948265296384ULL);
        if(!bindings || (local_read<uint8_t>(bindings+0x70)&1))return reject(6);
        const auto inner=local_read<uint64_t>(bindings+0x78);
        if(!inner || local_read<uint64_t>(inner)!=ops.base+0x6e136a0 || local_read<uint64_t>(inner+0x10)!=bindings ||
           local_read<uint32_t>(inner+0x30)!=1 || local_read<uint32_t>(inner+0x34)!=48 || local_read<uint32_t>(inner+0x44))return reject(7);
        const auto binding_type=local_read<uint64_t>(inner+0x70);
        if(!ops.script(binding_type,"MovieSceneBinding","/Script/MovieScene",48) ||
           !object_array_schema(binding_type,"Tracks",32,91198442210066952ULL,"MovieSceneTrack","/Script/MovieScene"))return reject(8);
        const auto cut=ops.field(scene_class,"CameraCutTrack",240,8,0x6e11d38,94012710941360648ULL);
        if(!cut || !ops.named(local_read<uint64_t>(cut+0x70),"MovieSceneTrack","/Script/MovieScene"))return reject(9);
        std::array<Identity,512> tracks{};unsigned track_count=0;
        const auto add_track=[&](uint64_t object,bool allow_camera_alias) {
            auto id=Native::capture(ops.base,object);
            if(!valid(id) || local_read<uint64_t>(object+32)!=scene.address || !valid_hierarchy(local_read<uint64_t>(object+16)) ||
               !ancestor(local_read<uint64_t>(object+16),"MovieSceneTrack","/Script/MovieScene"))return false;
            for(unsigned i=0;i<track_count;++i)if(same(tracks[i],id))return allow_camera_alias;
            if(track_count==tracks.size())return false;
            tracks[track_count++]=id;return true;
        };
        const auto add_array_track=[&](uint64_t object) {return add_track(object,false);};
        if(!pointer_array(scene.address+224,add_array_track))return reject(10);
        const auto bh=local_read<e33_camera_binding::ObjectArray>(scene.address+128);
        if(!array_header(bh,48,512))return reject(11);
        for(int32_t i=0;i<bh.count;++i)if(!pointer_array(bh.data+uint64_t(i)*48+32,add_array_track))return reject(12);
        const auto bh_after=local_read<e33_camera_binding::ObjectArray>(scene.address+128);
        if(std::memcmp(&bh,&bh_after,sizeof(bh)))return reject(13);
        const auto camera=local_read<uint64_t>(scene.address+240);
        if(camera && !add_track(camera,true))return reject(14);
        for(unsigned i=0;i<track_count;++i) {
            const auto track=tracks[i];if(!valid(track))return reject(15);
            const auto subtrack=ancestor(local_read<uint64_t>(track.address+16),"MovieSceneSubTrack","/Script/MovieScene");
            if(!subtrack)continue;
            if(!object_array_schema(subtrack,"Sections",152,82200039048348168ULL,"MovieSceneSection","/Script/MovieScene"))return reject(16);
            std::array<Identity,512> sections{};unsigned section_count=0;
            const auto add_section=[&](uint64_t object) {
                auto id=Native::capture(ops.base,object);
                if(!valid(id) || local_read<uint64_t>(object+32)!=track.address)return false;
                const auto cls=local_read<uint64_t>(object+16);
                if(!valid_hierarchy(cls) ||
                   !ancestor(cls,"MovieSceneSubSection","/Script/MovieScene"))return false;
                for(unsigned j=0;j<section_count;++j)if(same(sections[j],id))return true;
                if(section_count==sections.size())return false;
                sections[section_count++]=id;return true;
            };
            if(!pointer_array(track.address+152,add_section))return reject(17);
            for(unsigned j=0;j<section_count;++j) {
                const auto section=sections[j];const auto cls=local_read<uint64_t>(section.address+16);
                const auto subsection=ancestor(cls,"MovieSceneSubSection","/Script/MovieScene");
                const auto sub=subsection ? ops.field(subsection,"SubSequence",304,8,0x6e11d38,84451357825696257ULL) : 0;
                if(!sub || !ops.named(local_read<uint64_t>(sub+0x70),"MovieSceneSequence","/Script/MovieScene") || !valid(section))return reject(18);
                const auto child=local_read<uint64_t>(section.address+304);
                if(child && !sink(Native::capture(ops.base,child)))return reject(19);
                if(local_read<uint64_t>(section.address+304)!=child || !valid(section))return reject(20);
            }
        }
        if(!(valid(sequence) && valid(scene) && local_read<uint64_t>(sequence.address+movie_offset)==scene.address &&
            local_read<uint64_t>(scene.address+240)==camera && context()))return reject(21);
        return true;
    }
};
