#pragma once
#include "bound_camera_proof.h"
#include "bound_object_frame.h"
#include "enum_schema.h"
#include "target_pod_schema.h"

// Positive authored declaration, not arbitrary GUID lookup. QueryOps is the
// exact TargetBoundObjectQuery adapter. Dynamic absence remains a separately
// verified engine-semantic predicate: the exact null Function field makes
// 142d5ef00/142d553c0 return before FieldPath access. Never zero-test FFieldPath.
template<class QueryOps>
bool authored_camera_spawn(QueryOps& ops,const e33_camera_binding::Guid& guid,
    CallIdentity& object_template) {
    object_template={};
    if(!ops.context() || !ops.valid(ops.asset) ||
       !e33_camera_binding::allowed(ops.profile,guid))return false;
    const auto cls=local_read<uint64_t>(ops.asset.address+16);
    if(!call_is_class(ops.base,cls) || !ops.named(cls,"LevelSequence","/Script/LevelSequence"))return false;
    auto scene_field=ops.field(cls,"MovieScene",112,8,0x6e11d38,79938962105827848ULL);
    if(!scene_field)return false;
    auto scene_class=local_read<uint64_t>(scene_field+0x70);
    if(!call_is_class(ops.base,scene_class) || !ops.named(scene_class,"MovieScene","/Script/MovieScene"))return false;
    auto scene=call_capture(ops.base,local_read<uint64_t>(ops.asset.address+112));
    if(!ops.valid(scene) || local_read<uint64_t>(scene.address+16)!=scene_class)return false;
    auto array=ops.field(scene_class,"Spawnables",96,16,0x6e0de80,18014398509482496ULL);
    if(!array || (local_read<uint8_t>(array+0x70)&1))return false;
    auto inner=local_read<uint64_t>(array+0x78);
    if(!inner || local_read<uint64_t>(inner)!=ops.base+0x6e136a0 || local_read<uint64_t>(inner+0x10)!=array ||
       local_read<uint32_t>(inner+0x30)!=1 || local_read<uint32_t>(inner+0x34)!=240 || local_read<uint32_t>(inner+0x44))return false;
    auto spawn=local_read<uint64_t>(inner+0x70);
    if(!ops.script(spawn,"MovieSceneSpawnable","/Script/MovieScene",240))return false;
    auto guid_field=ops.field(spawn,"Guid",160,16,0x6e136a0,20266268116386304ULL);
    auto template_field=ops.field(spawn,"ObjectTemplate",192,8,0x6e11d38,93449760987415040ULL);
    auto ownership=ops.field(spawn,"Ownership",216,1,0x6deeee8,20266268116386304ULL);
    auto dynamic=ops.field(spawn,"DynamicBinding",120,40,0x6e136a0,4503599627370497ULL);
    auto respawn=ops.field(spawn,"bContinuouslyRespawn",112,1,0x6e119b0,6755469234274817ULL);
    auto network_name=ops.field(spawn,"bNetAddressableName",113,1,0x6e119b0,6755469234274817ULL);
    if(!respawn || !network_name || local_read<uint32_t>(respawn+0x70)!=0xff010001 || local_read<uint32_t>(network_name+0x70)!=0xff010001)return false;
    if(!guid_field || !template_field || !ownership || !dynamic ||
       !ops.script(local_read<uint64_t>(guid_field+0x70),"Guid","/Script/CoreUObject",16) ||
       !ops.named(local_read<uint64_t>(template_field+0x70),"Object","/Script/CoreUObject"))return false;
    auto dynamic_type=call_capture(ops.base,local_read<uint64_t>(dynamic+0x70));
    if(!ops.valid(dynamic_type) || !ops.script(dynamic_type.address,"MovieSceneDynamicBinding","/Script/MovieScene",40))return false;
    auto function=ops.field(dynamic_type.address,"Function",0,8,0x6e11d38,79938962105303552ULL);
    auto params=ops.field(dynamic_type.address,"ResolveParamsProperty",8,32,0x6def080,6755399441055744ULL);
    if(!function || !params || !ops.named(local_read<uint64_t>(function+0x70),"Function","/Script/CoreUObject"))return false;
    auto enum_id=call_capture(ops.base,local_read<uint64_t>(ownership+0x78));
    TargetPodSchemaOps schema{ops.base};
    if(!ops.named(enum_id.address,"ESpawnOwnership","/Script/MovieScene") || !validate_byte_enum_parameter(schema,ownership,enum_id))return false;
    const auto enum_data=local_read<uint64_t>(enum_id.address+0x40);
    if(local_read<int32_t>(enum_id.address+0x48)!=4)return false;
    const char* members[]={"ESpawnOwnership::InnerSequence","ESpawnOwnership::RootSequence","ESpawnOwnership::External","ESpawnOwnership::ESpawnOwnership_MAX"};
    for(unsigned i=0;i<4;++i)if(!exact_name(ops.base,enum_data+i*16,members[i]) || local_read<int64_t>(enum_data+i*16+8)!=i)return false;
    const auto header=local_read<e33_camera_binding::ObjectArray>(scene.address+96);
    const int32_t expected=ops.profile==e33_camera_binding::Profile::locomotive ? 2 : 14;
    if(header.count!=expected || header.capacity<header.count || header.capacity>256 || !header.data ||
       (header.data&7) || header.data>UINT64_MAX-uint64_t(header.capacity)*240)return false;
    unsigned matches=0;
    for(int32_t i=0;i<header.count;++i) {
        const auto entry=header.data+uint64_t(i)*240;
        const auto observed=local_read<e33_camera_binding::Guid>(entry+160);
        if(!e33_camera_binding::same(guid,observed))continue;
        if(++matches!=1 || local_read<uint8_t>(entry+112) || local_read<uint8_t>(entry+113) || local_read<uint8_t>(entry+216)>1 || local_read<uint64_t>(entry+120))return false;
        auto candidate=call_capture(ops.base,local_read<uint64_t>(entry+192));
        if(!ops.valid(candidate))return false;
        auto camera_class=local_read<uint64_t>(candidate.address+16);
        if(!call_is_class(ops.base,camera_class) || !ops.named(camera_class,"CineCameraActor","/Script/CinematicCamera"))return false;
        object_template=candidate;
    }
    auto after=local_read<e33_camera_binding::ObjectArray>(scene.address+96);
    return matches==1 && !std::memcmp(&header,&after,sizeof(header)) && ops.valid(scene) &&
        ops.valid(object_template) && ops.valid(ops.asset) && ops.context();
}
