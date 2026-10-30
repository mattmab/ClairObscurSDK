#pragma once
#include "bound_object_frame.h"
#include "invocation_protocol.h"
#include <array>

namespace e33_authored_guid {
using e33_camera_binding::ObjectArray;
// The reader is supplied by the native adapter or a deterministic fixture.
// Snapshots include every GUID so duplicates introduced during a read reject.
template<class Reader>
bool unique_stable(Reader& reader,const ObjectArray (&headers)[2],const uint32_t (&guid)[4]) {
    const uint32_t sizes[]{240,128},guid_offsets[]{160,56};
    std::array<std::array<std::array<uint32_t,4>,512>,2> snapshots{};
    unsigned matches=0;
    for(unsigned kind=0;kind<2;++kind) {
        const auto h=headers[kind];
        if(h.count<0 || h.capacity<h.count || h.count>512 || h.capacity>4096 ||
           (h.capacity && (!h.data || (h.data&7))) || (!h.capacity && h.data) ||
           h.data>UINT64_MAX-uint64_t(h.capacity)*sizes[kind])return false;
        for(int32_t i=0;i<h.count;++i) {
            auto& value=snapshots[kind][i];
            const auto address=h.data+uint64_t(i)*sizes[kind]+guid_offsets[kind];
            for(unsigned j=0;j<4;++j)value[j]=reader.word(address+j*4);
            if(!std::memcmp(value.data(),guid,16) && ++matches>1)return false;
        }
    }
    for(unsigned kind=0;kind<2;++kind) {
        const auto h=headers[kind],after=reader.header(kind);
        if(std::memcmp(&h,&after,sizeof(h)))return false;
        for(int32_t i=0;i<h.count;++i)for(unsigned j=0;j<4;++j)
            if(snapshots[kind][i][j]!=reader.word(h.data+uint64_t(i)*sizes[kind]+guid_offsets[kind]+j*4))return false;
    }
    return matches==1 && reader.context();
}
}

// Research-only exact-build membership proof for one retained LevelSequence.
// This does NOT prove occurrence under a playback root or select an instance.
// The caller must run it on the game thread and separately hold/revalidate the
// source and its owned player. Nothing is loaded or mutated here.
template<class Ops>
bool authored_guid_membership(Ops& ops,const CallIdentity& source,const uint32_t (&guid)[4]) {
    using e33_camera_binding::ObjectArray;
    if(!ops.context() || !ops.valid(source) || !(guid[0]||guid[1]||guid[2]||guid[3]))return false;
    const auto cls=local_read<uint64_t>(source.address+16);
    if(!call_is_class(ops.base,cls) || !ops.named(cls,"LevelSequence","/Script/LevelSequence"))return false;
    const auto field=ops.field(cls,"MovieScene",112,8,0x6e11d38,79938962105827848ULL);
    if(!field || !ops.named(local_read<uint64_t>(field+0x70),"MovieScene","/Script/MovieScene"))return false;
    const auto scene=call_capture(ops.base,local_read<uint64_t>(source.address+112));
    if(!ops.valid(scene) || local_read<uint64_t>(scene.address+16)!=local_read<uint64_t>(field+0x70) ||
       local_read<uint64_t>(scene.address+32)!=source.address)return false;
    const auto scene_class=local_read<uint64_t>(scene.address+16);
    const char* names[]{"Spawnables","Possessables"};
    const char* types[]{"MovieSceneSpawnable","MovieScenePossessable"};
    const uint32_t offsets[]{96,112},sizes[]{240,128},guid_offsets[]{160,56};
    ObjectArray headers[2]{};
    for(unsigned kind=0;kind<2;++kind) {
        const auto array=ops.field(scene_class,names[kind],offsets[kind],16,0x6e0de80,18014398509482496ULL);
        if(!array || (local_read<uint8_t>(array+0x70)&1))return false;
        const auto inner=local_read<uint64_t>(array+0x78);
        if(!inner || local_read<uint64_t>(inner)!=ops.base+0x6e136a0 || local_read<uint64_t>(inner+0x10)!=array ||
           local_read<uint32_t>(inner+0x30)!=1 || local_read<uint32_t>(inner+0x34)!=sizes[kind] ||
           local_read<uint32_t>(inner+0x44))return false;
        const auto declaration=local_read<uint64_t>(inner+0x70);
        if(!ops.script(declaration,types[kind],"/Script/MovieScene",sizes[kind]))return false;
        const auto member=ops.field(declaration,"Guid",guid_offsets[kind],16,0x6e136a0,20266268116386304ULL);
        if(!member || !ops.script(local_read<uint64_t>(member+0x70),"Guid","/Script/CoreUObject",16))return false;
        headers[kind]=local_read<ObjectArray>(scene.address+offsets[kind]);
    }
    struct Reader {
        Ops& ops;uint64_t scene;
        uint32_t word(uint64_t address)const{return local_read<uint32_t>(address);}
        ObjectArray header(unsigned kind)const{return local_read<ObjectArray>(scene+(kind?112:96));}
        bool context()const{return ops.context();}
    } reader{ops,scene.address};
    return e33_authored_guid::unique_stable(reader,headers,guid) && ops.valid(source) && ops.valid(scene) &&
        local_read<uint64_t>(source.address+112)==scene.address &&
        local_read<uint64_t>(scene.address+32)==source.address && ops.context();
}
