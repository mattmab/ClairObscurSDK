#define NOMINMAX
#include <windows.h>
#include "target_authored_sequence_occurrence.h"
#include <cassert>
#include <cstring>
#include <map>
#include <string>
#include <vector>

// In-process synthetic object graph for the real occurrence adapter. Its
// capture/class policy alone is replaced; field/array/ownership traversal is
// the production adapter running against byte-addressed test memory.
struct alignas(8) Block {
    unsigned char data[512]{};
    uint64_t at() const {return reinterpret_cast<uint64_t>(data);}
    template<class T> void put(size_t offset,T value) {std::memcpy(data+offset,&value,sizeof value);}
};
struct FakeNative {
    inline static std::map<uint64_t,CallIdentity> objects;
    inline static std::map<uint64_t,bool> classes;
    static bool is_class(uint64_t,uint64_t p) {return classes.count(p)!=0;}
    static CallIdentity capture(uint64_t,uint64_t p) {
        auto it=objects.find(p);return it==objects.end() ? CallIdentity{-1,0,0} : it->second;
    }
    static CallIdentity add(Block& b,bool cls=false) {
        CallIdentity id{static_cast<int32_t>(objects.size()+1),1,b.at()};
        objects[b.at()]=id;if(cls)classes[b.at()]=true;return id;
    }
};
struct Field {uint64_t owner;std::string name;uint32_t offset,width;uint64_t table,flags,address;};
struct FakeOps {
    uint64_t base=0x100000000ULL;
    bool live=true;
    std::map<uint64_t,std::pair<std::string,std::string>> names;
    std::vector<Field> fields;
    bool context()const{return live;}
    bool valid(const CallIdentity& id)const {
        auto it=FakeNative::objects.find(id.address);
        return it!=FakeNative::objects.end() && std::memcmp(&it->second,&id,sizeof(id))==0;
    }
    bool same(const CallIdentity& a,const CallIdentity& b)const{return !std::memcmp(&a,&b,sizeof(a));}
    bool named(uint64_t p,const char* name,const char* package)const {
        auto it=names.find(p);return it!=names.end() && it->second.first==name && it->second.second==package;
    }
    uint64_t field(uint64_t owner,const char* name,uint32_t offset,uint32_t width,uint64_t table,uint64_t flags)const {
        for(const auto& f:fields)if(f.owner==owner && f.name==name && f.offset==offset && f.width==width && f.table==table && f.flags==flags)return f.address;
        return 0;
    }
    bool script(uint64_t p,const char* name,const char* package,uint32_t width)const {
        return named(p,name,package) && local_read<uint32_t>(p+0x58)==width;
    }
    void name(Block& b,const char* n,const char* p) {names[b.at()]={n,p};}
    void field_def(Block& owner,const char* name,uint32_t offset,uint32_t width,uint64_t table,uint64_t flags,Block& field) {
        fields.push_back({owner.at(),name,offset,width,table,flags,field.at()});
    }
};
using Reader=TargetAuthoredOccurrenceReader<FakeOps,FakeNative>;
using ObjectArray=e33_camera_binding::ObjectArray;

struct Fixture {
    FakeOps ops;
    Block level,template_type,camera_type,sequence_type,scene_type,track_type,subtrack_type,section_type,subsection_type,binding_type;
    Block root,child,root_scene,child_scene,track,section;
    Block level_movie,template_movie,tracks_prop,tracks_inner,bindings_prop,bindings_inner,binding_tracks,binding_tracks_inner,cut_prop,sections_prop,sections_inner,subsequence_prop;
    uint64_t tracks[1]{},sections[1]{};
    CallIdentity root_id{},child_id{};
    Fixture() {
        FakeNative::objects.clear();FakeNative::classes.clear();
        for(auto* c:{&level,&template_type,&camera_type,&sequence_type,&scene_type,&track_type,&subtrack_type,&section_type,&subsection_type})FakeNative::add(*c,true);
        FakeNative::add(binding_type);root_id=FakeNative::add(root);child_id=FakeNative::add(child);
        FakeNative::add(root_scene);FakeNative::add(child_scene);FakeNative::add(track);FakeNative::add(section);
        ops.name(level,"LevelSequence","/Script/LevelSequence");ops.name(template_type,"TemplateSequence","/Script/TemplateSequence");
        ops.name(camera_type,"CameraAnimationSequence","/Script/TemplateSequence");ops.name(sequence_type,"MovieSceneSequence","/Script/MovieScene");
        ops.name(scene_type,"MovieScene","/Script/MovieScene");ops.name(track_type,"MovieSceneTrack","/Script/MovieScene");
        ops.name(subtrack_type,"MovieSceneSubTrack","/Script/MovieScene");ops.name(section_type,"MovieSceneSection","/Script/MovieScene");
        ops.name(subsection_type,"MovieSceneSubSection","/Script/MovieScene");ops.name(binding_type,"MovieSceneBinding","/Script/MovieScene");
        camera_type.put(0x40,template_type.at());camera_type.put<uint32_t>(0x58,232);template_type.put(0x40,sequence_type.at());
        template_type.put<uint32_t>(0x58,232);sequence_type.put<uint32_t>(0x58,104);binding_type.put<uint32_t>(0x58,48);
        subtrack_type.put(0x40,track_type.at());subsection_type.put(0x40,section_type.at());
        root.put(16,level.at());root.put(112,root_scene.at());child.put(16,camera_type.at());child.put(104,child_scene.at());
        root_scene.put(16,scene_type.at());root_scene.put(32,root.at());child_scene.put(16,scene_type.at());child_scene.put(32,child.at());
        track.put(16,subtrack_type.at());track.put(32,root_scene.at());section.put(16,subsection_type.at());section.put(32,track.at());section.put(304,child.at());
        tracks[0]=track.at();sections[0]=section.at();root_scene.put(224,ObjectArray{reinterpret_cast<uint64_t>(tracks),1,1});
        track.put(152,ObjectArray{reinterpret_cast<uint64_t>(sections),1,1});
        ops.field_def(level,"MovieScene",112,8,0x6e11d38,79938962105827848ULL,level_movie);
        ops.field_def(template_type,"MovieScene",104,8,0x6e11d38,79938962105827848ULL,template_movie);
        level_movie.put(0x70,scene_type.at());template_movie.put(0x70,scene_type.at());
        array_prop(scene_type,"Tracks",224,91198442210066952ULL,tracks_prop,tracks_inner,track_type);
        ops.field_def(scene_type,"ObjectBindings",128,16,0x6e0de80,18014948265296384ULL,bindings_prop);
        bindings_prop.put(0x78,bindings_inner.at());bindings_inner.put<uint64_t>(0,ops.base+0x6e136a0);bindings_inner.put(0x10,bindings_prop.at());
        bindings_inner.put<uint32_t>(0x30,1);bindings_inner.put<uint32_t>(0x34,48);bindings_inner.put(0x70,binding_type.at());
        array_prop(binding_type,"Tracks",32,91198442210066952ULL,binding_tracks,binding_tracks_inner,track_type);
        ops.field_def(scene_type,"CameraCutTrack",240,8,0x6e11d38,94012710941360648ULL,cut_prop);cut_prop.put(0x70,track_type.at());
        array_prop(subtrack_type,"Sections",152,82200039048348168ULL,sections_prop,sections_inner,section_type);
        ops.field_def(subsection_type,"SubSequence",304,8,0x6e11d38,84451357825696257ULL,subsequence_prop);subsequence_prop.put(0x70,sequence_type.at());
    }
    void array_prop(Block& owner,const char* name,uint32_t offset,uint64_t flags,Block& prop,Block& inner,Block& type) {
        ops.field_def(owner,name,offset,16,0x6e0de80,flags,prop);prop.put(0x78,inner.at());inner.put<uint64_t>(0,ops.base+0x6e11d38);
        inner.put(0x10,prop.at());inner.put<uint32_t>(0x30,1);inner.put<uint32_t>(0x34,8);inner.put(0x70,type.at());
    }
};
int main() {
    Fixture f;Reader r{f.ops};e33_authored_occurrence::Proof<CallIdentity> proof;
    assert(proof.unique(r,f.root_id,f.child_id));
    assert(proof.unique(r,f.root_id,f.root_id));
    f.child.put(16,f.template_type.at());assert(proof.unique(r,f.root_id,f.child_id));f.child.put(16,f.camera_type.at());
    f.camera_type.put<uint32_t>(0x58,231);assert(!proof.unique(r,f.root_id,f.child_id) && r.failure==2);f.camera_type.put<uint32_t>(0x58,232);
    f.template_movie.put<uint64_t>(0x70,0);assert(!proof.unique(r,f.root_id,f.child_id) && r.failure==3);f.template_movie.put(0x70,f.scene_type.at());
    f.child_scene.put<uint64_t>(32,f.root.at());assert(!proof.unique(r,f.root_id,f.child_id) && r.failure==4);f.child_scene.put<uint64_t>(32,f.child.at());
    f.tracks_inner.put<uint32_t>(0x34,4);assert(!proof.unique(r,f.root_id,f.child_id) && r.failure==5);f.tracks_inner.put<uint32_t>(0x34,8);
    f.ops.fields[3].flags=0;assert(!proof.unique(r,f.root_id,f.child_id) && r.failure==6);f.ops.fields[3].flags=18014948265296384ULL;
    f.bindings_inner.put<uint32_t>(0x34,47);assert(!proof.unique(r,f.root_id,f.child_id) && r.failure==7);f.bindings_inner.put<uint32_t>(0x34,48);
    f.binding_tracks_inner.put<uint64_t>(0x10,0);assert(!proof.unique(r,f.root_id,f.child_id) && r.failure==8);f.binding_tracks_inner.put(0x10,f.binding_tracks.at());
    f.cut_prop.put<uint64_t>(0x70,0);assert(!proof.unique(r,f.root_id,f.child_id) && r.failure==9);f.cut_prop.put(0x70,f.track_type.at());
    f.root_scene.put(224,ObjectArray{reinterpret_cast<uint64_t>(f.tracks),2,1});assert(!proof.unique(r,f.root_id,f.child_id) && r.failure==10);f.root_scene.put(224,ObjectArray{reinterpret_cast<uint64_t>(f.tracks),1,1});
    f.root_scene.put(128,ObjectArray{0,-1,0});assert(!proof.unique(r,f.root_id,f.child_id) && r.failure==11);f.root_scene.put(128,ObjectArray{});
    f.section.put<uint64_t>(32,f.root_scene.at());assert(!proof.unique(r,f.root_id,f.child_id) && r.failure==17);f.section.put<uint64_t>(32,f.track.at());
    f.subsequence_prop.put<uint64_t>(0x70,0);assert(!proof.unique(r,f.root_id,f.child_id) && r.failure==18);f.subsequence_prop.put(0x70,f.sequence_type.at());
    // A mutation during enumeration must not be accepted as a stable graph.
    auto changing=[&](const CallIdentity&) {f.section.put<uint64_t>(304,f.root.at());return true;};
    assert(!r.children(f.root_id,changing) && r.failure==20);f.section.put<uint64_t>(304,f.child.at());
    // Duplicated pointers inside one section array are rejected, not collapsed.
    uint64_t repeated_section[2]{f.section.at(),f.section.at()};
    f.track.put(152,ObjectArray{reinterpret_cast<uint64_t>(repeated_section),2,2});
    assert(!proof.unique(r,f.root_id,f.child_id) && r.failure==17);
    f.track.put(152,ObjectArray{reinterpret_cast<uint64_t>(f.sections),1,1});
    // The same rule applies within one track array, but an ordinary
    // CameraCutTrack alias of an already enumerated track is deduplicated.
    uint64_t repeated_track[2]{f.track.at(),f.track.at()};
    f.root_scene.put(224,ObjectArray{reinterpret_cast<uint64_t>(repeated_track),2,2});
    assert(!proof.unique(r,f.root_id,f.child_id) && r.failure==10);
    f.root_scene.put(224,ObjectArray{reinterpret_cast<uint64_t>(f.tracks),1,1});
    f.root_scene.put(240,f.track.at());assert(proof.unique(r,f.root_id,f.child_id));f.root_scene.put<uint64_t>(240,0);
    // A track listed in the master array and a binding array cannot be
    // assumed to represent just one occurrence. Only the separate camera-cut
    // property is an accepted alias.
    Block binding_row;binding_row.put(32,ObjectArray{reinterpret_cast<uint64_t>(f.tracks),1,1});
    f.root_scene.put(128,ObjectArray{binding_row.at(),1,1});
    assert(!proof.unique(r,f.root_id,f.child_id) && r.failure==12);
    f.root_scene.put(128,ObjectArray{});
    // Two separate sections referencing the same source are two occurrences.
    Block duplicate;FakeNative::add(duplicate);duplicate.put(16,f.subsection_type.at());duplicate.put(32,f.track.at());duplicate.put(304,f.child.at());
    uint64_t duplicates[2]{f.section.at(),duplicate.at()};f.track.put(152,ObjectArray{reinterpret_cast<uint64_t>(duplicates),2,2});
    assert(!proof.unique(r,f.root_id,f.child_id));f.track.put(152,ObjectArray{reinterpret_cast<uint64_t>(f.sections),1,1});
    f.section.put<uint64_t>(304,f.root.at());assert(!proof.unique(r,f.root_id,f.root_id));f.section.put<uint64_t>(304,f.child.at());
    f.ops.live=false;assert(!proof.unique(r,f.root_id,f.child_id));
}
