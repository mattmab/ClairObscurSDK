#pragma once
#include "enemy_arena_binding.h"
#include "enemy_arena_assembly.h"
#include "owned_arena_value.h"
namespace e33_enemy_spawn {
class EngineArenaBinding {
    uint64_t base_=0,world_=0,target_=0,descriptor_=0,layers_=0;
    CallIdentity actor_{},arena_{},library_{},convert_{},resolve_{};
    alignas(8) uint8_t conversion_[48]{},resolution_[48]{};
    OwnedArenaValue owned_value_{};
    bool value_mode_=false;
    void* presentation_owner_=nullptr;
    bool (*presentation_owned_)(void*,uint64_t,const CallIdentity&,uint64_t)=nullptr;
    static bool copy_ready(uint64_t b){
        return local_read<uint64_t>(b+0x6e128d8+0xf0)==b+0x1368190&&
            local_read<uint8_t>(b+0x1368190)==0x45&&local_read<uint8_t>(b+0x1368191)==0x85&&local_read<uint8_t>(b+0x1368192)==0xc9;
    }
    void copy(void* to,const void* from){
        reinterpret_cast<void(__fastcall*)(void*,void*,const void*,int)>(base_+0x1368190)(reinterpret_cast<void*>(descriptor_),to,from,1);
    }
    bool function(CallIdentity identity,bool resolution)const{
        using namespace e33_mesh;
        const auto fn=call_identity(base_,identity),library=call_identity(base_,library_);
        static const MeshField convert_fields[]={
            {"Object","ObjectProperty",0,8,6755468160533120ULL,0x6e11d38ULL,"","",0,"",0,"Object"},
            {"ReturnValue","SoftObjectProperty",8,40,7881299347899776ULL,0x6e128d8ULL,"","",0,"",0,""}};
        static const MeshField resolve_fields[]={
            {"SoftObject","SoftObjectProperty",0,40,7881299482116482ULL,0x6e128d8ULL,"","",0,"",0,""},
            {"ReturnValue","ObjectProperty",40,8,6755468160534400ULL,0x6e11d38ULL,"","",0,"",0,"Object"}};
        if(!fn||!library||!named(base_,library,"Default__KismetSystemLibrary","/Script/Engine")||
           !named(base_,local_read<uint64_t>(fn+32),"KismetSystemLibrary","/Script/Engine")||
           !exact_name(base_,fn+24,resolution?"Conv_SoftObjectReferenceToObject":"Conv_ObjectToSoftObjectReference")||
           local_read<uint32_t>(fn+0xb0)!=(resolution?339878915U:335684611U)||
           local_read<uint16_t>(fn+0xb6)!=48||local_read<uint16_t>(fn+0xb8)!=(resolution?40:8)||
           local_read<int32_t>(fn+0x58)!=48||local_read<uint64_t>(fn+0xd8)!=base_+(resolution?0x383b380:0x383a400)||
           !fields(base_,fn,resolution?resolve_fields:convert_fields,2)||
           !call_derives(base_,local_read<uint64_t>(library+16),local_read<uint64_t>(fn+32)))return false;
        const auto pe=local_read<uint64_t>(local_read<uint64_t>(library)+0x268);
        return pe==base_+0x1393330||pe==base_+0x332bb90;
    }
    bool invoke(CallIdentity identity,bool resolution,void* frame){
        if(!TargetPodSchemaOps{base_}.context()||!function(identity,resolution))return false;
        const auto library=call_identity(base_,library_),fn=call_identity(base_,identity);
        const auto pe=local_read<uint64_t>(local_read<uint64_t>(library)+0x268);
        reinterpret_cast<void(__fastcall*)(void*,void*,void*)>(pe)(reinterpret_cast<void*>(library),reinterpret_cast<void*>(fn),frame);
        return true;
    }
public:
    void configure(uint64_t b,uint64_t world,CallIdentity actor,CallIdentity arena,
                   CallIdentity library,CallIdentity convert,CallIdentity resolve){
        base_=b;world_=world;actor_=actor;arena_=arena;library_=library;convert_=convert;resolve_=resolve;
        presentation_owner_=nullptr;presentation_owned_=nullptr;
    }
    void configure_owned_value(uint64_t b,uint64_t world,CallIdentity actor,CallIdentity arena,
                   CallIdentity library,CallIdentity convert,CallIdentity resolve){
        configure(b,world,actor,arena,library,convert,resolve);value_mode_=true;
    }
    // Same engine-owned value transaction for another retained SDK actor. The
    // consumer supplies live ownership proof; no actor property is fabricated.
    void configure_owned_presentation_value(uint64_t b,uint64_t world,CallIdentity actor,CallIdentity arena,
                   CallIdentity library,CallIdentity convert,CallIdentity resolve,void* owner,
                   bool (*owned)(void*,uint64_t,const CallIdentity&,uint64_t)){
        configure_owned_value(b,world,actor,arena,library,convert,resolve);
        presentation_owner_=owner;presentation_owned_=owned;
    }
    bool preflight(){
        if(!TargetPodSchemaOps{base_}.context()||!call_identity(base_,actor_)||!call_identity(base_,arena_)||
           !arena_world(base_,actor_.address,world_)||!copy_ready(base_)||!function(convert_,false)||!function(resolve_,true))return false;
        ArenaAssemblyObservation observation{};
        if(observe_arena_assembly(base_,world_,arena_.address,observation))return false;
        if(value_mode_){
            if(presentation_owner_||presentation_owned_){
                if(!presentation_owner_||!presentation_owned_||!presentation_owned_(presentation_owner_,base_,actor_,world_))return false;
            }else if(!arena_class(base_,actor_.address,"BP_Battle_DummyEnemy_C","/Game/Characters/Enemies/Blueprints/BP_Battle_DummyEnemy"))return false;
            // The already validated conversion function supplies the exact soft
            // property descriptor. No Character-only property is fabricated.
            uint64_t found=0;unsigned count=0,walked=0;
            for(auto f=local_read<uint64_t>(convert_.address+0x50);f&&++walked<=8;f=local_read<uint64_t>(f+0x18)){
                if(!exact_name(base_,f+0x20,"ReturnValue"))continue;
                ++count;
                if(local_read<uint64_t>(f)==base_+0x6e128d8&&
                   local_read<uint64_t>(f+0x10)==(convert_.address|1)&&
                   local_read<uint32_t>(f+0x30)==1&&local_read<uint32_t>(f+0x34)==40&&
                   local_read<uint32_t>(f+0x44)==8)found=f;
            }
            if(walked>8||count!=1||!found)return false;
            descriptor_=found;target_=reinterpret_cast<uint64_t>(owned_value_.bytes);layers_=0;return true;
        }
        if(!arena_class(base_,actor_.address,"BP_jRPG_Enemy_World_Base_Seamless_C","/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_Enemy_World_Base_Seamless"))return false;
        const auto battle=picto_field(base_,actor_.address,"IsInBattle","BoolProperty",2930,1);
        if(!battle||local_read<uint8_t>(battle))return false;
        target_=picto_field(base_,actor_.address,"BattleMap_BP","SoftObjectProperty",2032,40,&descriptor_);
        uint64_t layer_descriptor=0;
        layers_=picto_field(base_,actor_.address,"BattleMapDataLayers","ArrayProperty",2072,16,&layer_descriptor);
        if(!target_||!descriptor_||local_read<uint64_t>(descriptor_)!=base_+0x6e128d8||!layers_||!layer_descriptor)return false;
        const auto inner=local_read<uint64_t>(layer_descriptor+0x78);
        if(!inner||local_read<uint64_t>(inner+16)!=layer_descriptor||local_read<int32_t>(inner+0x34)!=8||
           !exact_name(base_,local_read<uint64_t>(inner+8),"ObjectProperty")||
           !e33_mesh::named(base_,local_read<uint64_t>(inner+0x70),"DataLayerAsset","/Script/Engine"))return false;
        return true;
    }
    bool dependencies_supported(){
        if(value_mode_)return true; // No authored dependency array is borrowed or cleared.
        const auto count=local_read<int32_t>(layers_+8),capacity=local_read<int32_t>(layers_+12);
        // Nonempty authored dependencies require explicit same-map validation;
        // this operation never clears or substitutes the dependency array.
        return count==0&&capacity>=0&&capacity<=4096;
    }
    bool convert(){
        if(!call_identity(base_,arena_))return false;
        const auto object=arena_.address;std::memcpy(conversion_,&object,8);
        if(!invoke(convert_,false,conversion_))return false;
        return adopt_converted_arena_identity(arena_,call_capture(base_,object));
    }
    bool assign(){
        if(!TargetPodSchemaOps{base_}.context()||!call_identity(base_,actor_)||!copy_ready(base_))return false;
        if(value_mode_)return owned_value_.assign([&](void* to,const void* from){copy(to,from);},conversion_+8);
        copy(reinterpret_cast<void*>(target_),conversion_+8);return true;
    }
    bool close_owned_value(){
        return owned_value_.close([&](){return base_&&descriptor_&&TargetPodSchemaOps{base_}.context()&&copy_ready(base_)&&function(convert_,false);},
            [&](void* to,const void* from){copy(to,from);});
    }
    bool verify(){
        copy(resolution_,reinterpret_cast<const void*>(target_));
        if(!invoke(resolve_,true,resolution_))return false;
        return local_read<uint64_t>(reinterpret_cast<uint64_t>(resolution_+40))==arena_.address&&arena_live(base_,arena_.address);
    }
    bool clear_temporary(){
        if(!base_||!descriptor_||!TargetPodSchemaOps{base_}.context()||!copy_ready(base_))return false;
        const uint8_t empty[40]{};
        copy(conversion_+8,empty);copy(resolution_,empty);
        std::memset(conversion_,0,sizeof(conversion_));std::memset(resolution_,0,sizeof(resolution_));return true;
    }
    CallIdentity observed_arena()const{return call_capture(base_,arena_.address);}
    bool copy_soft_reference(void* destination){
        if(!destination||!preflight()||!dependencies_supported())return false;
        copy(destination,reinterpret_cast<const void*>(target_));return true;
    }
    bool verify_soft_reference(const void* source){
        if(!source||!preflight()||!dependencies_supported())return false;
        copy(resolution_,source);
        if(!invoke(resolve_,true,resolution_))return false;
        return local_read<uint64_t>(reinterpret_cast<uint64_t>(resolution_+40))==arena_.address&&arena_live(base_,arena_.address);
    }
};
}
