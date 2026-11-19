template<class Pool> void configure_story_world(uint64_t b,uint64_t session,Pool& pool,uint8_t* raw,size_t bytes,
        const CallPodValidation* pod,const CallEntryValidation* entry,
        uint32_t (*preflight)(void*,const CallPacket&),uint32_t (*capture)(void*,uint32_t,CallIdentity&)){
    using namespace e33_story_world;
    struct Ops {
        Owner& owner;uint64_t base,session;Pool& pool;
        const CallPodValidation* pod;const CallEntryValidation* entry;
        uint32_t (*preflight)(void*,const CallPacket&);uint32_t (*capture)(void*,uint32_t,CallIdentity&);
        bool current(const Header&h){
            if(!owner.timeline_only_||owner.owner_!=h.owner||!owner.lease_||!owner.preparing_world_||
               owner.construction_.phase!=e33_owned_actor::ConstructionPhase::Complete||
               !same(h.actor,owner.actor_)||!same(h.world,owner.ids_[2])||!same(h.controller,owner.ids_[0])||
               !owner.current(base)||!call_identity(base,h.actor)||!pool.owns_object(session,owner.lease_,h.actor.address))return false;
            const auto cls=local_read<uint64_t>(h.actor.address+16);
            const char* name=h.kind==1?"BP_InvisibleWall_NavModifier_C":"BP_jRPG_MapTeleportPoint_Interactible_C";
            const char* path=h.kind==1?"/Game/LevelTools/InvisibleWalls/BP_InvisibleWall_NavModifier":"/Game/LevelTools/BP_jRPG_MapTeleportPoint_Interactible";
            if(cls!=owner.ids_[4].address||!named(base,cls,name,path))return false;
            const auto player=zone_ref(base,h.controller.address,"Player"),viewport=zone_ref(base,player,"ViewportClient");
            if(!call_capture(base,player).address||!call_capture(base,viewport).address||
               !named(base,local_read<uint64_t>(player+16),"LocalPlayer","/Script/Engine")||
               zone_ref(base,player,"PlayerController")!=h.controller.address||zone_ref(base,viewport,"World")!=h.world.address)return false;
            for(const auto value:{h.world.address,h.controller.address,h.actor.address,player,viewport})
                if(local_read<uint32_t>(value+8)&0x40018030U)return false;
            if(!call_identity(base,h.root)||local_read<uint64_t>(h.root.address+32)!=h.actor.address||
               zone_ref(base,h.actor.address,"RootComponent")!=h.root.address||local_read<uint32_t>(h.root.address+8)&0x40018030U)return false;
            if(h.kind==1&&(!call_identity(base,h.mesh)||local_read<uint64_t>(h.mesh.address+32)!=h.actor.address||
               zone_ref(base,h.actor.address,"SM_InvisibleWalls")!=h.mesh.address||local_read<uint32_t>(h.mesh.address+8)&0x40018030U))return false;
            return true;
        }
        bool function_matches(const Header&h,uint32_t i,const RetainedCallPacket&p){
            const auto fn=call_identity(base,p.call.function);if(!fn)return false;
            const auto s=step(h,i);const auto cls=local_read<uint64_t>(fn+32);
            const auto expected=s==WallEnabled?"BP_InvisibleWall_NavModifier_C":
                (s==Movable||s==RestoreMobility||s==MeshScale)?"SceneComponent":"Actor";
            const auto path=s==WallEnabled?"/Game/LevelTools/InvisibleWalls/BP_InvisibleWall_NavModifier":"/Script/Engine";
            return named(base,cls,expected,path)&&exact_name(base,fn+24,function(s));
        }
        bool validate(const Header&h,uint32_t i,RetainedCallPacket&p){
            if(!current(h)||!function_matches(h,i,p))return false;
            // Existing SceneComponent layout already verified by placement
            // profiles; prevent restoring a stale originally observed byte.
            uint64_t descriptor=0;const auto mobility=picto_field(base,h.root.address,"Mobility","ByteProperty",395,1,&descriptor);
            if(!mobility||local_read<uint64_t>(descriptor)!=base+0x6e10420||local_read<uint8_t>(mobility)!=h.mobility)return false;
            CallRetention retention{&p,preflight,capture};
            return !reflected_call(base,p.call,&retention,pod,nullptr,nullptr,true,entry);
        }
        void dispatch(const Header&h,uint32_t i,RetainedCallPacket&p){
            if(!current(h)||!function_matches(h,i,p)){p.call.error=rejected;return;}
            CallRetention retention{&p,preflight,capture};
            p.call.error=reflected_call(base,p.call,&retention,pod,nullptr,nullptr,false,entry);
        }
    } ops{*this,b,session,pool,pod,entry,preflight,capture};
    run(raw,bytes,story_world_configuration_,ops);
}
void quarantine_story_world(){story_world_configuration_.attempted=true;story_world_configuration_.complete=false;}
