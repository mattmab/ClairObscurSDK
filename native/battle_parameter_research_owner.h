#pragma once
#include "target_battle_parameter_owner.h"
#include "target_battle_parameter_source.h"
#include "target_battle_parameter_policy.h"
#include "target_battle_entry.h"
#include "target_battle_parameter_arena.h"
#include "mesh_protocol.h"
#include <optional>
#include <memory>
#if defined(E33_RUNTIME_CINEMATIC_VERSION) && E33_RUNTIME_CINEMATIC_VERSION>=215
#include "battle_completion_owner.h"
#define E33_BATTLE_COMPLETION_RECEIPT_SESSION 1
#endif
#include "parameter_instance_authority.h"

namespace e33_enemy_spawn {
// Candidate-only owned source/parameter admission and guarded battle entry.
// Never executes a source GameAction or its surrounding campaign action chain.
class ParameterResearchOwner {
    std::optional<BattleParameterOwner> frame_;
    CallIdentity ids_[3]{}; // structure, source, root; stabilized after acquisition
    TargetParameterSourceProof proof_{};
    uint64_t owner_=0;
#ifdef E33_BATTLE_COMPLETION_RECEIPT_SESSION
    std::optional<BattleCompletionOwner> completion_;
    std::shared_ptr<void> completion_proof_;
    uint32_t completion_query(MeshPacket& packet){
        if(!completion_||packet.owner!=owner_){packet.error=3661;return 0;}
        auto* bytes=reinterpret_cast<uint8_t*>(&packet);
        e33_battle_completion::Receipt receipt{};
        const bool returned=completion_->take(owner_,receipt);
        const uint32_t fields[]={0x52423345,1,returned?static_cast<uint32_t>(receipt.result):0U,
            returned?2U:static_cast<uint32_t>(completion_->state())};
        std::memcpy(bytes+4096,fields,16);
        const uint64_t keys[]={owner_,returned?receipt.generation:0};std::memcpy(bytes+4112,keys,16);
        if(returned){const e33_battle_completion::Identity ids[]={receipt.world,receipt.controller,receipt.source,receipt.arena};
            std::memcpy(bytes+4128,ids,sizeof(ids));}
        packet.state=1;return 0;
    }
#endif
    CallIdentity entry_ids_[2]{};
    ParameterLease entry_leases_[2]{};
    std::array<uint8_t,344> original_{};
    template<class Pool> TargetBattleParameterOwnerOps<Pool> operations(uint64_t b,uint64_t session,Pool& pool) {
        return {{b,session,pool,ids_[0],ids_[1],ids_[2],0,0,0,&proof_,TargetParameterSourceProof::allowed}};
    }
    template<class Ops> uint32_t release_entry(Ops& ops){
        for(const auto& lease:entry_leases_)
            if(lease.state==ParameterLeaseState::AcquireUnknown||lease.state==ParameterLeaseState::ReleaseUnknown)return 408;
        for(unsigned i=2;i>0;--i){
            auto& lease=entry_leases_[i-1];
            if(lease.state==ParameterLeaseState::Empty||lease.state==ParameterLeaseState::Released)continue;
            if(lease.state!=ParameterLeaseState::Held)return 408;
            lease.state=ParameterLeaseState::ReleaseUnknown;
            const auto result=ops.release_token(lease.token);
            if(result==ParameterCall::NotDispatched){lease.state=ParameterLeaseState::Held;return 407;}
            if(result!=ParameterCall::Completed)return 408;
            lease.state=ParameterLeaseState::Released;
        }
        return 0;
    }
public:
    bool protects(uint64_t token)const{
#ifdef E33_BATTLE_COMPLETION_RECEIPT_SESSION
        return completion_&&completion_->protects(token);
#else
        (void)token;return false;
#endif
    }
    bool holds_resources()const{return (frame_&&(frame_->pending()||frame_->quarantined()))
#ifdef E33_BATTLE_COMPLETION_RECEIPT_SESSION
        || (completion_&&completion_->active())
#endif
        ;}
    template<class Pool> uint32_t close(uint64_t b,uint64_t session,Pool& pool) {
#ifdef E33_BATTLE_COMPLETION_RECEIPT_SESSION
        if(completion_){const auto error=completion_->close(b,session,pool);if(error)return error;
            completion_.reset();completion_proof_.reset();}
#endif
        if(!frame_)return 0;
        if(frame_->quarantined())return 408;
        if(frame_->entry_state()==BattleEntryState::Returned)return 407;
        auto ops=operations(b,session,pool);
        const auto released=release_entry(ops);if(released)return released;
        if(!frame_->close(ops))return frame_->quarantined()?408:407;
        if(frame_->pending())return 408;
        frame_.reset();owner_=0;
        for(auto& id:ids_)id={};
        for(auto& id:entry_ids_)id={};
        for(auto& lease:entry_leases_)lease={};
        return 0;
    }
    template<class Pool,class EnemyOwner> void command(uint64_t b,uint64_t session,Pool& pool,MeshPacket& packet,EnemyOwner& fallback,
            ParameterInstanceAuthority<Pool> authority={}) {
        using ProofOwner=ParameterProofOwner<Pool,EnemyOwner>;
        ProofOwner enemy{fallback,authority};
        auto* bytes=reinterpret_cast<uint8_t*>(&packet);
        if(packet.version!=3||packet.operation<124||(packet.operation>130
#ifdef E33_BATTLE_COMPLETION_RECEIPT_SESSION
            && packet.operation!=160
#endif
            )||packet.error||packet.state||!packet.owner){packet.error=3050;return;}
        std::array<uint8_t,sizeof(MeshPacket)> canonical{};
        const uint32_t header[]={3,packet.operation,0,0};
        std::memcpy(canonical.data(),header,sizeof(header));
        std::memcpy(canonical.data()+16,&packet.owner,8);
        if(packet.operation!=126&&packet.operation!=160)std::memcpy(canonical.data()+88,bytes+88,sizeof(ids_));
#ifdef E33_BATTLE_COMPLETION_RECEIPT_SESSION
        if(packet.operation==160){
            if(std::memcmp(canonical.data(),bytes,canonical.size())){packet.error=3050;return;}
            completion_query(packet);return;
        }
        uint32_t want_completion=0;
        if(packet.operation==130){std::memcpy(&want_completion,bytes+48,4);
            if(want_completion>1){packet.error=3050;return;}std::memcpy(canonical.data()+48,&want_completion,4);}
#endif
        uint32_t mode=0,arena_policy=0;uint64_t anchor_owner=0;CallIdentity anchor{};
        const bool entry_requested=packet.operation>=128;
        const bool arena_requested=packet.operation>=129;
        const bool dispatch_requested=packet.operation==130;
        const bool policy_requested=packet.operation>=127;
        if(!authority.valid()){packet.error=3050;return;}
        if(authority.owns&&((entry_requested&&!authority.entry)||(arena_requested&&(!authority.arena||!authority.copy_arena))||(dispatch_requested&&!authority.dispatch))){packet.error=3060;return;}
        if(policy_requested){
            std::memcpy(&mode,bytes+32,4);std::memcpy(&anchor_owner,bytes+40,8);
            std::memcpy(&anchor,bytes+136,sizeof(anchor));
            if(mode>2||!anchor_owner||(dispatch_requested&&mode!=1&&mode!=2)){packet.error=3050;return;}
            std::memcpy(canonical.data()+32,&mode,4);std::memcpy(canonical.data()+40,&anchor_owner,8);
            std::memcpy(canonical.data()+136,&anchor,sizeof(anchor));
        }
        if(entry_requested)std::memcpy(canonical.data()+152,bytes+152,sizeof(entry_ids_));
        if(arena_requested){
            std::memcpy(&arena_policy,bytes+36,4);if(arena_policy>1){packet.error=3050;return;}
            std::memcpy(canonical.data()+36,&arena_policy,4);
        }
        if(std::memcmp(canonical.data(),bytes,canonical.size())){packet.error=3050;return;}
        if(owner_&&owner_!=packet.owner){packet.error=3051;return;}
        if(packet.operation==126){packet.error=close(b,session,pool);if(!packet.error)packet.state=1;return;}
        if(frame_){packet.error=3052;return;}
        CallIdentity query[3]{};std::memcpy(query,bytes+88,sizeof(query));
        proof_.base=b;
        TargetBattleParameterOwnerOps<Pool> ops{{b,session,pool,query[0],query[1],query[2],0,0,0,&proof_,TargetParameterSourceProof::allowed}};
        if(!ops.admit()){packet.error=3053;return;}
        if(mode==2&&!e33_mesh::named(b,query[2].address,"DA_GA_SQT_ScielJoinsGroup_P2_Tutorial",
            "/Game/Levels/GestralVillage/GameActions/DA_GA_SQT_ScielJoinsGroup_P2_Tutorial")){packet.error=3050;return;}
        uint64_t instance_name=0;
        if(policy_requested&&!(authority.owns?
            authority.owns(authority.owner,b,session,pool,anchor_owner,anchor,instance_name):
            enemy.owned_instance_name(b,session,pool,anchor_owner,anchor,instance_name))){packet.error=3057;return;}
        CallIdentity entry_query[2]{};
        if(entry_requested){
            std::memcpy(entry_query,bytes+152,sizeof(entry_query));
            if(!enemy.owned_entry_context(b,session,pool,anchor_owner,anchor,entry_query[0],entry_query[1],instance_name)){packet.error=3060;return;}
        }
        if(packet.operation==124){const uint32_t result[]={1,0,0};std::memcpy(bytes+4096,result,sizeof(result));packet.state=1;return;}
        owner_=packet.owner;
        std::memcpy(ids_,query,sizeof(ids_));
        std::memcpy(original_.data(),reinterpret_cast<const void*>(query[1].address+48),original_.size());
        frame_.emplace(); // persistent before the first lease/engine operation
        const bool copied=frame_->open(ops);
        ids_[0]=ops.engine.structure;ids_[1]=ops.engine.source;ids_[2]=ops.engine.root;
        if(!copied){packet.error=3054;return;}
        if(!ops.engine.source_profile_ready()||std::memcmp(original_.data(),reinterpret_cast<const void*>(ids_[1].address+48),original_.size())){packet.error=3055;return;}
        if(arena_requested){
            const ParameterLease held[]={frame_->lease(0),frame_->lease(1),frame_->lease(2)};
            TargetBattleParameterArenaOps<Pool,ProofOwner> arena_ops{ops.frame_ops(held),enemy,anchor_owner,anchor,arena_policy==1};
            if(!frame_->bind_arena(arena_ops)){packet.error=frame_->quarantined()?408:arena_ops.rejection;return;}
        }
        uint32_t party_before=0,party_after=0;
        if(policy_requested){
            const auto count=local_read<int32_t>(reinterpret_cast<uint64_t>(frame_->copied_data())+208);
            if(count<0||count>64){packet.error=3059;return;}party_before=static_cast<uint32_t>(count);
            struct InstanceProof {
                uint64_t base,session,token;Pool& pool;ProofOwner& enemy;CallIdentity actor;
                ParameterInstanceAuthority<Pool> authority;
                static bool verify(void* context,uint64_t expected){
                    auto& proof=*static_cast<InstanceProof*>(context);uint64_t observed=0;
                    return (proof.authority.owns?proof.authority.owns(proof.authority.owner,proof.base,proof.session,proof.pool,proof.token,proof.actor,observed):
                        proof.enemy.owned_instance_name(proof.base,proof.session,proof.pool,proof.token,proof.actor,observed))&&observed==expected;
                }
            } instance{b,session,anchor_owner,pool,enemy,anchor,authority};
            const ParameterLease held[]={frame_->lease(0),frame_->lease(1),frame_->lease(2)};
            TargetBattleParameterPolicyOps<Pool> policy_ops{ops.frame_ops(held),
                {static_cast<ParameterPolicyMode>(mode),instance_name},&instance,InstanceProof::verify};
            if(!frame_->apply_policy(policy_ops)){packet.error=3058;return;}
            party_after=local_read<uint32_t>(reinterpret_cast<uint64_t>(frame_->copied_data())+208);
            if(!ops.engine.source_profile_ready()||std::memcmp(original_.data(),reinterpret_cast<const void*>(ids_[1].address+48),original_.size())){packet.error=3055;return;}
        }
        if(entry_requested){
            for(unsigned i=0;i<2;++i){
                entry_ids_[i]=entry_query[i];auto& lease=entry_leases_[i];
                lease.state=ParameterLeaseState::AcquireUnknown;
                const auto result=ops.acquire_identity(entry_ids_[i],lease.token);
                if(result==ParameterCall::NotDispatched&&!lease.token){lease.state=ParameterLeaseState::Empty;packet.error=3061;return;}
                if(result!=ParameterCall::Completed||!lease.token){packet.error=408;return;}
                lease.state=ParameterLeaseState::Held;
            }
            struct EntryProof {
                uint64_t base,session,token,name;Pool& pool;ProofOwner& enemy;CallIdentity actor;BattleParameterOwner& parameters;
                static bool verify(void* context,const void* data,const CallIdentity& manager,const CallIdentity& function){
                    auto& proof=*static_cast<EntryProof*>(context);uint64_t observed=0;
                    return proof.parameters.frame_state()==ParameterFrameState::PolicyApplied&&data==proof.parameters.copied_data()&&
                        proof.enemy.owned_entry_context(proof.base,proof.session,proof.pool,proof.token,proof.actor,manager,function,observed)&&
                        observed==proof.name&&local_read<uint64_t>(reinterpret_cast<uint64_t>(data)+16)==observed;
                }
                static bool begin(void* context,const void* data,const CallIdentity& manager,const CallIdentity& function){
                    auto& proof=*static_cast<EntryProof*>(context);
                    return verify(context,data,manager,function)&&proof.enemy.note_entry_dispatch(
                        proof.base,proof.session,proof.pool,proof.token,proof.actor,manager,function);
                }
            } entry{b,session,anchor_owner,instance_name,pool,enemy,anchor,*frame_};
            const ParameterLease held[]={frame_->lease(0),frame_->lease(1),frame_->lease(2)};
            TargetBattleEntryOps<Pool> entry_ops{ops.frame_ops(held),entry_ids_[0],entry_ids_[1],
                entry_leases_[0].token,entry_leases_[1].token,&entry,EntryProof::verify,nullptr,EntryProof::begin};
            if(!entry_ops.entry_preflight(frame_->copied_data())){packet.error=3062;return;}
            if(dispatch_requested){
#ifdef E33_BATTLE_COMPLETION_RECEIPT_SESSION
                if(want_completion){
                    // Source/world/arena/private ID originate in the existing
                    // owned transaction. No caller FName or function is trusted.
                    struct CompletionProof {
                        ParameterResearchOwner* parent;uint64_t base,session,token,name;
                        Pool* pool;EnemyOwner* fallback;ParameterInstanceAuthority<Pool> authority;
                        CallIdentity anchor,source,arena;
                        static bool verify(void* opaque,const e33_battle_completion::Context& c,bool post){
                            auto& p=*static_cast<CompletionProof*>(opaque);uint64_t name=0;CallIdentity arena{};
                            ParameterProofOwner<Pool,EnemyOwner> enemy{*p.fallback,p.authority};
                            const auto held=p.fallback->staged_actor();
                            const bool native_registration=p.parent->owner_==c.battle&&p.parent->owner_&&
                                p.authority.owner==p.fallback&&p.fallback->has_work()&&p.fallback->is_trigger_anchor()&&
                                p.fallback->token_matches(p.token)&&held.index==p.anchor.index&&
                                held.serial==p.anchor.serial&&held.address==p.anchor.address&&
                                call_identity(p.base,p.anchor)&&call_identity(p.base,p.source)&&call_identity(p.base,p.arena)&&
                                !(local_read<uint32_t>(p.anchor.address+8)&0x40018030U)&&
                                !(local_read<uint32_t>(p.source.address+8)&0x40018030U)&&
                                !(local_read<uint32_t>(p.arena.address+8)&0x40018030U)&&
                                local_read<uint64_t>(p.anchor.address+24)==p.name&&p.name==c.private_name&&
                                e33_battle_completion::same(c.source,{p.source.index,p.source.serial,p.source.address})&&
                                e33_battle_completion::same(c.arena,{p.arena.index,p.arena.serial,p.arena.address})&&
                                !std::memcmp(p.parent->original_.data(),reinterpret_cast<const void*>(p.source.address+48),344);
                            if(!native_registration)return false;
                            // POST runs under TraceSlots lock. Never call the
                            // broader owned-entry helpers here: they may update
                            // retirement journals. The already armed native
                            // source/arena/private-name registration is immutable.
                            if(post)return true;
                            return enemy.owned_instance_name(p.base,p.session,*p.pool,p.token,p.anchor,name)&&name==p.name&&
                                enemy.owned_entry_arena(p.base,p.session,*p.pool,p.token,p.anchor,arena)&&
                                arena.index==p.arena.index&&arena.serial==p.arena.serial&&arena.address==p.arena.address;
                        }
                    };
                    if(authority.owner!=&fallback||!fallback.is_trigger_anchor()){packet.error=3661;return;}
                    CallIdentity arena{};
                    if(!enemy.owned_entry_arena(b,session,pool,anchor_owner,anchor,arena)){packet.error=3661;return;}
                    e33_retired_world::TargetOps world_ops{b};e33_retired_world::Snapshot current{};
                    const auto controller=call_capture(b,local_read<uint64_t>(entry_ids_[0].address+32));
                    if(!world_ops.observe(current)||!world_ops.controller_world(controller,current.world)){packet.error=3661;return;}
                    const auto cls=local_read<uint64_t>(controller.address+16);
                    const bool worldmap=exact_name(b,cls+24,"BP_PlayerController_WorldMap_C")&&
                        exact_name(b,local_read<uint64_t>(cls+32)+24,"/Game/Gameplay/WorldMap/BP_PlayerController_WorldMap");
                    CallIdentity function{};unsigned found=0,steps=0;
                    for(auto child=local_read<uint64_t>(cls+0x48);child&&steps<256;++steps,child=local_read<uint64_t>(child+0x28)){
                        if(!call_capture(b,child).address){packet.error=3661;return;}
                        if(exact_name(b,child+24,"ResumeExplorationOnBattleEnd")&&local_read<uint64_t>(child+32)==cls){function=call_capture(b,child);++found;}
                    }
                    if(found!=1||steps==256){packet.error=3661;return;}
                    auto proof=std::make_shared<CompletionProof>(CompletionProof{this,b,session,anchor_owner,instance_name,
                        &pool,&fallback,authority,anchor,ids_[1],arena});
                    completion_proof_=proof;completion_.emplace();
                    const CallIdentity completion_ids[]={current.world,controller,ids_[1],arena,function};
                    const auto error=completion_->arm(b,session,pool,completion_ids,owner_,instance_name,worldmap,
                                                     proof.get(),CompletionProof::verify);
                    if(error){packet.error=error;return;}
                }
#endif
                if(!frame_->dispatch_entry(entry_ops)){packet.error=frame_->quarantined()?408:3064;return;}
                if(!frame_->confirm_entry_copy(entry_ops)){packet.error=3065;return;}
            }
        }
        // Do not clear the admission journal after this automatic cleanup. A
        // duplicate copy request is rejected until explicit close operation126.
        packet.error=release_entry(ops);if(packet.error)return;
        if(!frame_->close(ops)){packet.error=frame_->quarantined()?408:407;return;}
        if(!ops.engine.source_profile_ready()||std::memcmp(original_.data(),reinterpret_cast<const void*>(ids_[1].address+48),original_.size())){packet.error=3055;return;}
        const uint32_t result[]={1,1,1};std::memcpy(bytes+4096,result,sizeof(result));
        if(policy_requested){const uint32_t policy_result[]={mode,party_before,party_after,1};std::memcpy(bytes+4108,policy_result,sizeof(policy_result));}
        if(entry_requested){const uint32_t entry_result[]={1,dispatch_requested?1U:0U,dispatch_requested?1U:0U};std::memcpy(bytes+4124,entry_result,sizeof(entry_result));}
        if(arena_requested){const uint32_t arena_result[]={1,1,1};std::memcpy(bytes+4136,arena_result,sizeof(arena_result));}
        packet.state=1;
    }
};
}
