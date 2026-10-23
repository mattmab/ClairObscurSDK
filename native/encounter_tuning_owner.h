#pragma once
#include "encounter_tuning_policy.h"
#include "blueprint_direct_trace.h"
#include "stable_identity.h"

namespace e33_encounter_tuning {
// Per-owned-encounter stat initialization. No table, CDO, save or global
// difficulty manager writes. Hooks forward the original engine functions.
class Owner {
    uint64_t base_=0,token_=0,name_=0;DWORD thread_=0;
    CallIdentity ids_[6]{}; // world, controller, manager, owned actor, spawn, difficulty getter
    uint64_t leases_[6]{};size_t hooks_[2]{};
    uint64_t session_=0,pending_manager_lease_=0;void* pool_=nullptr;
    bool (*replace_manager_)(void*,Owner&,CallIdentity)=nullptr;
    Settings settings_{};bool routing_=false;RetryLifetime lifetime_{};
    uint32_t spawn_calls_=0,difficulty_calls_=0,error_=0;
    ScalarOverride<int32_t> level_{};ScalarOverride<double> health_{};ScalarOverride<uint8_t> difficulty_{};
    static bool named(uint64_t b,uint64_t o,const char* name,const char* package){
        return call_identity(b,call_capture(b,o))&&exact_name(b,o+24,name)&&
            exact_name(b,local_read<uint64_t>(o+32)+24,package);
    }
    bool owner_context()const {
        if(!base_||thread_!=GetCurrentThreadId()||!TargetPodSchemaOps{base_}.context())return false;
        for(unsigned i=0;i<2;++i)if(!call_identity(base_,ids_[i]))return false;
        for(auto o=ids_[1].address,n=uint64_t(0);o&&n<32;++n,o=local_read<uint64_t>(o+32))if(o==ids_[0].address)return true;
        return false;
    }
    bool context()const {
        return owner_context()&&call_identity(base_,ids_[2])&&
            local_read<uint64_t>(ids_[2].address+32)==ids_[1].address;
    }
    CallIdentity current_manager()const {
        if(!owner_context()||!call_identity(base_,ids_[4]))return {-1,0,0};
        // Exact live schema: controller property offset2336, flags and declared
        // type. Reuse the SDK's bounded property-reference validator.
        auto result=e33_mesh::skin_reference(base_,ids_[1],"BP_jRPG_Controller_World_C",
            "/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_Controller_World","AC_jRPG_BattleManager",
            2336,0x8001400080204ULL,"AC_jRPG_BattleManager_C");
        if(!result.address||(local_read<uint32_t>(result.address+8)&0x40018030U)||
           local_read<uint64_t>(result.address+32)!=ids_[1].address||
           local_read<uint64_t>(result.address+16)!=local_read<uint64_t>(ids_[4].address+32))return {-1,0,0};
        return result;
    }
    static bool same_identity(const CallIdentity& a,const CallIdentity& b){
        return a.index==b.index&&a.serial==b.serial&&a.address==b.address;
    }
    template<class Pool> bool replace_manager(Pool& pool,CallIdentity next){
        if(pending_manager_lease_||!same_identity(current_manager(),next))return false;
        TargetStrongReferenceOps ops{base_,next};
        if(pool.acquire(ops,session_,next.address,pending_manager_lease_)!=StrongLeaseResult::Ok||
           !stabilize_retained_identity(ops,next))return false;
        if(!same_identity(current_manager(),next))return false;
        restore(); // compare-before-restore on the retained previous manager
        TargetStrongReferenceOps release{base_,{-1,0,0}};
        if(pool.release(release,session_,leases_[2])!=StrongLeaseResult::Ok)return false;
        ids_[2]=next;leases_[2]=pending_manager_lease_;pending_manager_lease_=0;
        return true;
    }
    bool schema()const {
        for(const auto& id:ids_)if(!call_identity(base_,id))return false;
        const auto b=base_,m=ids_[2].address,cls=local_read<uint64_t>(m+16);
        if(!context()||!named(b,cls,"AC_jRPG_BattleManager_C","/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_BattleManager"))return false;
        uint64_t params=0,diff=0;
        if(!picto_field(b,m,"CurrentBattleStartParams","StructProperty",1224,344,&params)||
           !picto_field(b,m,"CurrentBattleEncounterLevel","IntProperty",1964,4)||
           !picto_field(b,m,"Challenge_EnemyHealthMultiplier","DoubleProperty",2552,8)||
           !picto_field(b,m,"BattleDifficulty","ByteProperty",2456,1,&diff)||
           !picto_field(b,m,"IsBattleInitialized","BoolProperty",168,1)||
           !picto_field(b,m,"HasBattleStartedEndFlow","BoolProperty",1961,1)||
           !picto_field(b,m,"Enemies","ArrayProperty",200,16))return false;
        if(!named(b,local_read<uint64_t>(params+0x70),"FBattleStartParams","/Game/Gameplay/Battle/FBattleStartParams")||
           !named(b,local_read<uint64_t>(diff+0x70),"E_GameDifficulty","/Game/Gameplay/Difficulty/E_GameDifficulty"))return false;
        for(unsigned i=0;i<2;++i){
            const auto f=ids_[4+i].address;
            if(local_read<uint64_t>(f+32)!=cls||!exact_name(b,f+24,i?"GetCurrentBattleDifficulty":"SpawnEnemyOnSpot")||
               local_read<uint16_t>(f+0xb6)!=(i?1:48)||local_read<uint16_t>(f+0xb8)!=(i?0:65535)||
               local_read<uint32_t>(f+0xb0)!=(i?0x1c420000U:0xcc20000U))return false;
        }
        return true;
    }
    bool active_battle()const {
        const auto m=ids_[2].address;
        return local_read<uint8_t>(m+168)||local_read<uint8_t>(m+1961)||local_read<int32_t>(m+208)>0;
    }
    bool matches()const{return context()&&local_read<uint64_t>(ids_[2].address+1240)==name_;}
    void before(void* object,void* frame){
        if(error_||!lifetime_.accepts_call())return;
        const auto fn=local_read<uint64_t>(reinterpret_cast<uint64_t>(frame)+0x10);
        if(fn!=ids_[4].address&&fn!=ids_[5].address)return;
        const auto manager=current_manager();
        if(!manager.address||manager.address!=reinterpret_cast<uint64_t>(object)||
           local_read<uint64_t>(manager.address+1240)!=name_)return;
        if(!same_identity(manager,ids_[2])&&
           (!replace_manager_||!replace_manager_(pool_,*this,manager))){error_=3640;return;}
        if(!matches())return;
        if(active_battle())lifetime_.observe_owned_call();
        const auto m=ids_[2].address;
        auto& difficulty=*reinterpret_cast<uint8_t*>(m+2456);
        if(settings_.difficulty>=0&&difficulty<=2){difficulty_.set(difficulty,static_cast<uint8_t>(settings_.difficulty));++difficulty_calls_;}
        if(fn!=ids_[4].address)return;
        auto& level=*reinterpret_cast<int32_t*>(m+1964);
        auto& hp=*reinterpret_cast<double*>(m+2552);
        if(level<0||level>10000||!std::isfinite(hp)||hp<0||hp>10000){error_=3636;return;}
        if(settings_.level_mode)level_.set(level,level_for(settings_,level_.baseline(level)));
        if(settings_.health!=1.){
            const auto authored=health_.baseline(hp);
            health_.set(hp,(authored>0?authored:1.)*settings_.health);
        }
        ++spawn_calls_;lifetime_.observe_owned_call();
    }
    static void callback(void* context,void* object,void* frame,void*){
        __try {static_cast<Owner*>(context)->before(object,frame);}
        __except(EXCEPTION_EXECUTE_HANDLER){static_cast<Owner*>(context)->error_=3637;}
    }
    void restore(){
        if(!context())return;
        const auto m=ids_[2].address;
        level_.restore(*reinterpret_cast<int32_t*>(m+1964));
        health_.restore(*reinterpret_cast<double*>(m+2552));
        difficulty_.restore(*reinterpret_cast<uint8_t*>(m+2456));
    }
public:
    bool has_work()const {for(auto t:leases_)if(t)return true;return pending_manager_lease_||routing_||hooks_[0]||hooks_[1];}
    template<class Pool> uint32_t close(uint64_t b,uint64_t session,Pool& pool){
        if(!has_work())return 0;
        if(!TargetStrongReferenceOps{b,{-1,0,0}}.can_release()||local_read<uint8_t>(b+0x9272cea))return 407;
        const auto current=current_manager();
        if(current.address&&local_read<uint64_t>(current.address+1240)==name_&&
           (local_read<uint8_t>(current.address+168)||local_read<uint8_t>(current.address+1961)||
            local_read<int32_t>(current.address+208)>0))return 407;
        restore();lifetime_.close();
        bool ok=true;
        for(auto& h:hooks_)if(h){
            if(context())ok=e33_trace::TraceSlots<>::remove(h)&&ok;
            else e33_trace::TraceSlots<>::detach(h);
            h=0;
        }
        if(routing_){ok=BlueprintDirectTrace::release_encounter()&&ok;routing_=false;}
        if(pending_manager_lease_){TargetStrongReferenceOps ops{b,{-1,0,0}};
            if(pool.release(ops,session,pending_manager_lease_)!=StrongLeaseResult::Ok)return 3638;
            pending_manager_lease_=0;}
        for(auto& lease:leases_)if(lease){TargetStrongReferenceOps ops{b,{-1,0,0}};
            if(pool.release(ops,session,lease)!=StrongLeaseResult::Ok)return 3638;lease=0;}
        return ok?0:3639;
    }
    template<class Pool> void poll(uint64_t,uint64_t,Pool&){
        // No ownership release on an empty roster: that is also the original
        // retry transition. Only close() retires the retained callbacks/leases.
        // matches() still gates every write to this exact owned encounter.
        if(has_work()&&context()&&!active_battle()&&lifetime_.observe_idle())restore();
    }
    template<class Pool,class Enemy,class Npc> void command(uint64_t b,uint64_t session,Pool& pool,MeshPacket& p,Enemy& enemy,Npc& npc){
        auto* bytes=reinterpret_cast<uint8_t*>(&p);std::array<uint8_t,sizeof(MeshPacket)> canonical{};
        std::memcpy(canonical.data(),bytes,24);
        if(p.version!=3||p.error||p.state||!p.owner||p.operation<157||p.operation>159){p.error=3630;return;}
        if(p.operation==157){std::memcpy(canonical.data()+24,bytes+24,24);std::memcpy(canonical.data()+88,bytes+88,sizeof(ids_));}
        if(std::memcmp(canonical.data(),bytes,sizeof(p))){p.error=3630;return;}
        if(p.operation!=157&&p.owner!=token_){p.error=3631;return;}
        if(p.operation==157){
            uint32_t kind=0;std::memcpy(&kind,bytes+24,4);Settings s;
            std::memcpy(&s.level_mode,bytes+28,4);std::memcpy(&s.level,bytes+32,4);std::memcpy(&s.difficulty,bytes+36,4);std::memcpy(&s.health,bytes+40,8);
            if(kind>1||!s.valid()||s.defaults()||has_work()){p.error=3630;return;}
            base_=b;thread_=GetCurrentThreadId();token_=p.owner;settings_=s;session_=session;pool_=&pool;
            replace_manager_=[](void* context,Owner& owner,CallIdentity manager){
                return owner.replace_manager(*static_cast<Pool*>(context),manager);
            };
            std::memcpy(ids_,bytes+88,sizeof(ids_));lifetime_={};spawn_calls_=difficulty_calls_=error_=0;
            level_={};health_={};difficulty_={};
            if(!schema()||!same_identity(current_manager(),ids_[2])||active_battle()||!(kind?npc.owned_parameter_instance_name(b,session,pool,token_,ids_[3],name_):
                enemy.owned_instance_name(b,session,pool,token_,ids_[3],name_))){p.error=3632;return;}
            for(unsigned i=0;i<6;++i){TargetStrongReferenceOps ops{b,ids_[i]};
                if(pool.acquire(ops,session,ids_[i].address,leases_[i])!=StrongLeaseResult::Ok||!stabilize_retained_identity(ops,ids_[i])){p.error=3633;return;}}
            if(!BlueprintDirectTrace::retain_encounter(b,ids_[4].address,ids_[5].address)){p.error=3634;return;}routing_=true;
            for(unsigned i=0;i<2;++i){hooks_[i]=e33_trace::TraceSlots<>::install(reinterpret_cast<void* volatile*>(ids_[4+i].address+0xd8),
                reinterpret_cast<e33_trace::Entry>(b+0x13937a0),callback,this,true,false);if(!hooks_[i]){p.error=3635;return;}}
        }else if(p.operation==159)p.error=close(b,session,pool);
        else poll(b,session,pool);
        const uint32_t report[]={has_work()?1U:0U,lifetime_.battle_observed()?1U:0U,lifetime_.restored()?1U:0U,spawn_calls_,difficulty_calls_,error_};
        std::memcpy(bytes+4096,report,sizeof(report));
        const double observed[]={double(level_.before),double(level_.written),health_.before,health_.written,double(difficulty_.before),double(difficulty_.written)};
        std::memcpy(bytes+4120,observed,sizeof(observed));if(!p.error)p.state=1;
    }
};
}
