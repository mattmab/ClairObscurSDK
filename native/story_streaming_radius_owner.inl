// One already constructed, retained source instance. The original source owns
// the array allocation; only its existing radius scalar is changed. Destroying
// this owned actor retires the setting with it, with no shared template writes.
template<class Pool> void configure_streaming_radius(uint64_t b,uint64_t session,Pool& pool,e33_story_streaming::Packet& p){
    using namespace e33_story_streaming;
    if(!valid(p)){p.error=rejected;return;}
    struct Ops {
        Owner& owner;uint64_t base,session;Pool& pool;const Packet& packet;
        bool observe(uint64_t& storage,Shape& shape){
            const auto& actor=owner.actor_;const auto& ids=owner.ids_;
            if(!owner.timeline_only_||owner.owner_!=packet.owner||!owner.lease_||
               owner.construction_.phase!=e33_owned_actor::ConstructionPhase::Complete||
               std::memcmp(&packet.actor,&actor,sizeof(actor))||!owner.current(base)||
               !call_identity(base,actor)||!pool.owns_object(session,owner.lease_,actor.address)||
               local_read<uint64_t>(actor.address+16)!=ids[4].address||
               !named(base,ids[4].address,"BP_WP_StreamingSourceComponent_C","/Game/Gameplay/GameplayElement/Content/StreamingSource/BP_WP_StreamingSourceComponent")||
               (local_read<uint32_t>(actor.address+8)&0x40018030U))return false;
            // A still-retained retired World/controller is not a current view.
            const auto player=zone_ref(base,ids[0].address,"Player"),viewport=zone_ref(base,player,"ViewportClient");
            if(!player||!viewport||zone_ref(base,player,"PlayerController")!=ids[0].address||
               zone_ref(base,viewport,"World")!=ids[2].address)return false;
            const CallIdentity component_id{packet.component.index,packet.component.serial,packet.component.address};
            const auto component=call_identity(base,component_id);
            if(!component||local_read<uint64_t>(component+32)!=actor.address||
               zone_ref(base,actor.address,"WorldPartitionStreamingSource")!=component||
               (local_read<uint32_t>(component+8)&0x40018030U))return false;
            const auto cls=local_read<uint64_t>(component+16);
            if(!call_is_class(base,cls)||!named(base,cls,"WorldPartitionStreamingSourceComponent","/Script/Engine")||
               local_read<int32_t>(cls+0x58)!=256)return false;
            uint64_t field=0;
            const auto array=picto_field(base,component,"Shapes","ArrayProperty",232,16,&field);
            if(!array||local_read<uint64_t>(field)!=base+0x6e0de80||local_read<uint64_t>(field+0x38)!=4503599627371013ULL||
               local_read<uint64_t>(field+16)!=(cls|1)||(local_read<uint8_t>(field+0x70)&1))return false;
            const auto inner=local_read<uint64_t>(field+0x78);
            if(!inner||local_read<uint64_t>(inner)!=base+0x6e136a0||local_read<uint64_t>(inner+16)!=field||
               !exact_name(base,local_read<uint64_t>(inner+8),"StructProperty")||
               local_read<int32_t>(inner+0x30)!=1||local_read<int32_t>(inner+0x34)!=72)return false;
            const auto schema=local_read<uint64_t>(inner+0x70);
            static const MeshField expected[]={
                {"bUseGridLoadingRange","BoolProperty",0,1,6755469234274821ULL,0x6e119b0,"","",0,"",0xff010001U,""},
                {"LoadingRangeScale","FloatProperty",4,4,6755469234274821ULL,0x6e11560,"","",0,"",0U,""},
                {"Radius","FloatProperty",8,4,6755469234274821ULL,0x6e11560,"","",0,"",0U,""},
                {"bIsSector","BoolProperty",12,1,6755469234274821ULL,0x6e119b0,"","",0,"",0xff010001U,""},
                {"SectorAngle","FloatProperty",16,4,6755469234274821ULL,0x6e11560,"","",0,"",0U,""},
                {"Location","StructProperty",24,24,6755469234274821ULL,0x6e136a0,"Vector","",0,"",0U,""},
                {"Rotation","StructProperty",48,24,4503669420589573ULL,0x6e136a0,"Rotator","",0,"",0U,""}};
            if(!call_capture(base,schema).address||!named(base,schema,"StreamingSourceShape","/Script/Engine")||
               local_read<int32_t>(schema+0x58)!=72||local_read<uint64_t>(schema+0x40)||!fields(base,schema,expected,7))return false;
            const auto data=local_read<uint64_t>(array);const auto count=local_read<int32_t>(array+8),capacity=local_read<int32_t>(array+12);
            if(!data||(data&7)||count!=1||capacity<1||capacity>8)return false;
            storage=data;std::memcpy(shape.bytes,reinterpret_cast<const void*>(data),sizeof(shape.bytes));return true;
        }
        bool write(uint64_t storage,float radius){
            uint64_t current=0;Shape shape{};
            if(!observe(current,shape)||current!=storage||!original_shape(shape))return false;
            std::memcpy(reinterpret_cast<void*>(storage+8),&radius,sizeof(radius));return true;
        }
    } ops{*this,b,session,pool,p};
    p.error=configure(streaming_radius_,p.radius,ops);if(!p.error)p.state=1;
}
