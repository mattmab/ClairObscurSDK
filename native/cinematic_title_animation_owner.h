#pragma once
#include "cinematic_title_animation_profile.h"
#include "cinematic_animation_quiescence.h"
#include "cinematic_animation_callbacks.h"
#include "strong_lease_pool.h"

// Shared with the widget journal: 16 track/widget pairs, at most one captured
// animation/player pair per widget, and five deduplicated profile identities.
constexpr size_t kTitleWidgetPairs=16;
constexpr size_t kTitlePrivateLeaseCapacity=kTitleWidgetPairs*(2+2)+5;
template<class Pool>
class TitleAnimationOwner {
    struct Entry {
        CallIdentity widget{},animation{},player{};
        e33_cinematic::AnimationDrain drain;
        bool captured=false,empty=false;
    };
    std::array<Entry,kTitleWidgetPairs> entries_{};
    size_t count_=0;
    uint64_t base_=0,session_=0;
    Pool* pool_=nullptr;
    TitleAnimationProfile profile_;
    CallIdentity title_class_{};
    bool profile_retained_=false,uncertain_=false;
    static bool read(uint64_t address,void* out,size_t size) {
        std::memcpy(out,reinterpret_cast<const void*>(address),size);return true;
    }
    bool retain(CallIdentity& value) {
        uint64_t token{};TargetStrongReferenceOps ops{base_,value};
        if(pool_->acquire(ops,session_,value.address,token)!=StrongLeaseResult::Ok) return false;
        value=call_capture(base_,value.address);return value.address!=0;
    }
    bool array(uint64_t object,uint32_t offset,uint64_t& data,int32_t& count) const {
        data=local_read<uint64_t>(object+offset);count=local_read<int32_t>(object+offset+8);
        const auto capacity=local_read<int32_t>(object+offset+12);
        return count>=0 && count<=capacity && capacity<=64 && (!capacity || (data && !(data&7)));
    }
    struct Ops {
        TitleAnimationOwner& owner;Entry& entry;
        bool associated() const {
            return call_identity(owner.base_,entry.widget) && call_identity(owner.base_,entry.animation) &&
                call_identity(owner.base_,entry.player) && owner.profile_.title(owner.base_,entry.widget) &&
                local_read<uint64_t>(entry.player.address+0x10)==owner.profile_.player.address &&
                local_read<uint64_t>(entry.player.address+0x210)==entry.animation.address &&
                fixed_slot(owner.base_,local_read<int32_t>(entry.player.address+0x218),
                    local_read<int32_t>(entry.player.address+0x21c))==entry.widget.address;
        }
        e33_cinematic::WidgetStep invoke(bool stop) {
            if(!associated()) return e33_cinematic::WidgetStep::uncertain;
            auto call=owner.profile_.call(entry.widget,entry.animation,stop);
            const auto error=reflected_call(owner.base_,call);
            if(error==201 && call.outcome==CallNotDispatched) return e33_cinematic::WidgetStep::deferred;
            if(error || call.outcome!=CallDispatchReturned) return e33_cinematic::WidgetStep::uncertain;
            if(!stop && !e33_cinematic::title_finished_callbacks_absent(read,entry.widget.address,entry.animation.address))
                return e33_cinematic::WidgetStep::uncertain;
            return e33_cinematic::WidgetStep::ok;
        }
        e33_cinematic::WidgetStep unbind_finished() { return invoke(false); }
        e33_cinematic::WidgetStep stop() {
            // Natural completion can already be restoring/draining this exact
            // retained player. Do not dispatch a duplicate stop in that case.
            if(!associated()) return e33_cinematic::WidgetStep::uncertain;
            if(!local_read<int32_t>(entry.player.address+0x274) ||
               (local_read<uint8_t>(entry.player.address+0x2ad)&1)) return e33_cinematic::WidgetStep::ok;
            return invoke(true);
        }
        e33_cinematic::AnimationQuiescence quiescence() {
            if(!associated() ||
               !e33_cinematic::title_finished_callbacks_absent(read,entry.widget.address,entry.animation.address))
                return e33_cinematic::AnimationQuiescence::uncertain;
            return e33_cinematic::title_animation_quiescence(read,entry.widget.address,entry.player.address);
        }
    };
public:
    bool safe_to_release() const {
        if(uncertain_) return false;
        for(size_t i=0;i<count_;++i)
            if(!entries_[i].empty && !entries_[i].drain.finished()) return false;
        return true;
    }
    bool prepare(uint64_t base,const CallIdentity& user) { return profile_.prepare(base,user); }
    void begin(uint64_t base,uint64_t session,Pool& pool) {
        base_=base;session_=session;pool_=&pool;count_=0;entries_={};
        title_class_={};profile_retained_=uncertain_=false;
    }
    bool register_widget(const CallIdentity& widget) {
        if(uncertain_) return false;
        for(size_t i=0;i<count_;++i)
            if(!std::memcmp(&entries_[i].widget,&widget,sizeof(widget))) return true;
        uncertain_=true;
        if(count_==kTitleWidgetPairs || !profile_.title(base_,widget)) return false;
        const auto cls=call_capture(base_,local_read<uint64_t>(widget.address+0x10));
        if(title_class_.address && std::memcmp(&cls,&title_class_,sizeof(cls))) return false;
        if(!profile_retained_) {
            if(pool_->preflight(session_,5)!=StrongLeaseResult::Ok) return false;
            title_class_=cls;
            if(!retain(profile_.animation) || !retain(profile_.player) || !retain(profile_.stop) ||
               !retain(profile_.unbind) || !retain(title_class_)) return false;
            profile_retained_=true;
        }
        entries_[count_++].widget=widget;uncertain_=false;return true;
    }
    e33_cinematic::WidgetStep close_widget(const CallIdentity& widget) {
        using namespace e33_cinematic;
        if(uncertain_) return WidgetStep::uncertain;
        Entry* entry=nullptr;
        for(size_t i=0;i<count_;++i)
            if(!std::memcmp(&entries_[i].widget,&widget,sizeof(widget))) { entry=&entries_[i];break; }
        if(!entry) return WidgetStep::uncertain;
        if(entry->empty) return WidgetStep::ok;
        uncertain_=true;
        if(!profile_.title(base_,widget)) return WidgetStep::uncertain;
        if(!entry->captured) {
            uint64_t queued{},active{},stopped{};int32_t queued_count{},active_count{},stopped_count{};
            if(!array(widget.address,544,queued,queued_count) || !array(widget.address,560,active,active_count) ||
               !array(widget.address,584,stopped,stopped_count)) return WidgetStep::uncertain;
            // Let engine-owned transitions finish naturally. Never flush the
            // global manager or select a different widget's animation player.
            if(queued_count || stopped_count) { uncertain_=false;return WidgetStep::deferred; }
            const auto animation=local_read<uint64_t>(widget.address+800);
            if(!animation && !active_count) {
                uint64_t callbacks{};int32_t callback_count{};
                if(!array(widget.address,696,callbacks,callback_count) || callback_count)
                    return WidgetStep::uncertain;
                entry->empty=true;uncertain_=false;return WidgetStep::ok;
            }
            // A nonnull animation with no active player could be an earlier
            // hidden-widget removal. Without a retained player its deferred
            // stop/root state cannot be proven, so do not release ownership.
            if(!animation || active_count!=1 || pool_->preflight(session_,2)!=StrongLeaseResult::Ok)
                return WidgetStep::uncertain;
            entry->animation=call_capture(base_,animation);
            if(!entry->animation.address || !call_derives(base_,local_read<uint64_t>(animation+0x10),profile_.animation.address))
                return WidgetStep::uncertain;
            if(active_count) {
                const auto player=local_read<uint64_t>(active);entry->player=call_capture(base_,player);
                if(!entry->player.address || local_read<uint64_t>(player+0x10)!=profile_.player.address ||
                   local_read<uint64_t>(player+0x210)!=animation ||
                   fixed_slot(base_,local_read<int32_t>(player+0x218),local_read<int32_t>(player+0x21c))!=widget.address)
                    return WidgetStep::uncertain;
            }
            if(!retain(entry->animation) || (entry->player.address && !retain(entry->player))) return WidgetStep::uncertain;
            entry->captured=true;
        }
        Ops ops{*this,*entry};const auto result=entry->drain.close(ops);
        if(result!=WidgetStep::uncertain) uncertain_=false;
        return result;
    }
};
