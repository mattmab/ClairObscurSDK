#pragma once
#include <array>
#include <cstdint>
#include <cstring>

namespace e33_camera_binding {
// Same-build GetBoundObjects parameters: 24-byte binding value followed by a
// 16-byte native TArray<UObject*>. No wire packet ever contains this allocation.
struct BindingValue {uint32_t guid[4];int32_t sequence_id,resolve_parent_index;};
struct ObjectArray {uint64_t data;int32_t count,capacity;};
static_assert(sizeof(BindingValue)==24 && sizeof(ObjectArray)==16);
enum class QueryResult {ok,empty,rejected,deferred,unknown};
template<class Identity>
class BoundObjectFrame {
    struct Parameters {BindingValue binding{};ObjectArray returned{};};
    static_assert(sizeof(Parameters)==40);
    alignas(16) Parameters arguments_{};
    std::array<Identity,8> identities_{};
    uint32_t count_=0;
    enum State {idle,dispatching,returned,freeing,complete,uncertain} state_=idle;
public:
    bool quarantined()const{return state_==dispatching || state_==returned || state_==freeing || state_==uncertain;}
    uint32_t count()const{return state_==complete ? count_ : 0;}
    const Identity* identities()const{return state_==complete ? identities_.data() : nullptr;}
    template<class Ops> QueryResult query(Ops& ops,const BindingValue& binding) {
        if(state_!=idle)return QueryResult::rejected;
        if(!ops.context())return QueryResult::deferred;
        // Native adapter must validate full function/struct/array profile,
        // retained player/actor/asset association and proven root ID semantics.
        if(!ops.validate(binding))return QueryResult::rejected;
        arguments_.binding=binding;
        state_=dispatching;
        ops.dispatch(&arguments_); // Exception preserves durable uncertain frame.
        state_=returned;
        if(!ops.context() || !ops.validate(binding) || std::memcmp(&arguments_.binding,&binding,sizeof(binding))) {
            state_=uncertain;return QueryResult::unknown;
        }
        const auto header=arguments_.returned;
        if(header.count<0 || header.capacity<header.count || header.count>8 || header.capacity>64 ||
           (header.capacity && (!header.data || (header.data&7))) ||
           (!header.capacity && header.data) || header.data>UINT64_MAX-uint64_t(header.capacity)*8) {
            state_=uncertain;return QueryResult::unknown;
        }
        // Capture and retain before freeing array storage or publishing values.
        for(int32_t i=0;i<header.count;++i) {
            uint64_t object{};
            if(!ops.read_pointer(header.data+uint64_t(i)*8,object) || !object ||
               !ops.capture(object,identities_[i])) {state_=uncertain;return QueryResult::unknown;}
            for(int32_t j=0;j<i;++j)if(ops.same(identities_[i],identities_[j])) {state_=uncertain;return QueryResult::unknown;}
            state_=uncertain; // Acquisition may fault with a published holder.
            if(!ops.retain(identities_[i]))return QueryResult::unknown;
            count_=static_cast<uint32_t>(i+1);state_=returned;
        }
        // The exact thunk transfers ownership to this return header. Its elements
        // are borrowed UObject pointers; only the array allocation is freed.
        if(std::memcmp(&arguments_.returned,&header,sizeof(header)) || !ops.context()) {
            state_=uncertain;return QueryResult::unknown;
        }
        if(header.data) {state_=freeing;ops.free_array(header.data);}
        arguments_.returned={};state_=complete;
        return count_ ? QueryResult::ok : QueryResult::empty;
    }
    template<class Ops> bool reset(Ops& ops) {
        if((state_!=idle && state_!=complete) || !ops.context() || !ops.outputs_released())return false;
        arguments_={};identities_={};count_=0;state_=idle;return true;
    }
};
}
