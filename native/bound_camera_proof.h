#pragma once
#include <array>
#include <cstdint>
#include <cstring>

namespace e33_camera_binding {
struct Guid {uint32_t words[4];};
inline bool same(const Guid& a,const Guid& b){return !std::memcmp(&a,&b,sizeof(a));}
// These are decoded authored ROOT spawnable GUIDs, not transient object indices.
// Locomotive's GUID is also Scavenger CAM05: profile + asset identity is mandatory.
enum class Profile:uint32_t {none=0,locomotive=1,scavenger=2};
inline bool allowed(Profile profile,const Guid& id) {
    constexpr Guid locomotive{{3868951513u,1230066568u,4000387518u,2702779930u}};
    constexpr Guid scavenger[]{
        {{3988227725u,1180247986u,2957613748u,2506576614u}},
        {{3323003479u,1294590874u,1110749852u,1552315500u}},
        {{2344242829u,1133825144u,963959480u,2788480762u}},
        {{101576481u,1074155408u,1436868279u,3861576507u}},
        locomotive};
    if(profile==Profile::locomotive)return same(id,locomotive);
    if(profile==Profile::scavenger)for(const auto& candidate:scavenger)if(same(id,candidate))return true;
    return false;
}

// Internal journal consumes an authenticated native binding query, never wire
// claims or an active-camera observation. Ops must check the live exact asset
// profile, retained factory-created player/actor association, root binding ID,
// absence of binding overrides, and spawned-object membership.
template<class Identity>
class Proof {
    struct Entry {Guid binding{};Identity camera{};};
    std::array<Entry,5> entries_{};
    uint32_t count_=0;uint64_t session_=0;
    Profile profile_=Profile::none;
    Identity player_{},asset_{};
    bool quarantined_=false;
public:
    bool quarantined() const {return quarantined_;}
    uint32_t count() const {return count_;}
    template<class Ops> bool begin(Ops& ops,uint64_t session,Profile profile,const Identity& player,const Identity& asset) {
        if(session_ || !session || profile==Profile::none || !ops.context() ||
           !ops.profile_asset(profile,asset) || !ops.owned_player_asset(player,asset) || !ops.no_overrides(player))return false;
        session_=session;profile_=profile;player_=player;asset_=asset;return true;
    }
    template<class Ops> bool admit(Ops& ops,uint64_t session,const Guid& binding) {
        if(!session_ || session!=session_ || quarantined_ || !allowed(profile_,binding) ||
           !ops.context() || !ops.profile_asset(profile_,asset_) || !ops.owned_player_asset(player_,asset_) ||
           !ops.no_overrides(player_))return false;
        for(uint32_t i=0;i<count_;++i)if(same(entries_[i].binding,binding))return false;
        if(count_==entries_.size())return false;
        Identity camera{};
        // Must require exactly ONE returned object for this root authored GUID,
        // with frame/array cleanup already acknowledged before this returns.
        if(!ops.single_bound_camera(player_,asset_,binding,camera) ||
           !ops.spawned_by_player(player_,asset_,binding,camera))return false;
        for(uint32_t i=0;i<count_;++i)if(ops.same(entries_[i].camera,camera))return false;
        quarantined_=true; // Publish uncertainty before strong acquisition.
        if(!ops.retain(camera) || !ops.valid(camera) ||
           !ops.owned_player_asset(player_,asset_) || !ops.no_overrides(player_))return false;
        entries_[count_++]={binding,camera};quarantined_=false;return true;
    }
    template<class Ops> bool matches(Ops& ops,uint64_t session,const Identity& player,const Identity& camera) const {
        if(!session_ || session!=session_ || quarantined_ || !ops.context() || !ops.same(player_,player) ||
           !ops.valid(camera) || !ops.profile_asset(profile_,asset_) || !ops.owned_player_asset(player_,asset_) ||
           !ops.no_overrides(player_))return false;
        // Historical positive binding evidence survives Stop/unbinding; the
        // private strong reference and full session/serial identity must remain.
        for(uint32_t i=0;i<count_;++i)if(ops.same(entries_[i].camera,camera))return ops.held(camera);
        return false;
    }
    // Native owner invokes only after camera restoration and acknowledged pool
    // release; clearing this journal does not itself release native references.
    template<class Ops> bool released(Ops& ops) {
        if(quarantined_ || !ops.context() || !ops.holds_empty())return false;
        *this={};return true;
    }
};
}
