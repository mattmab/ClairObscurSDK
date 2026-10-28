#define NOMINMAX
#include <windows.h>
#include "authored_portable_resolver.h"
#include "strong_lease_pool.h"
#include <cassert>
#include <stdexcept>

using namespace e33_authored_binding;
using e33_camera_binding::BindingValue;
using e33_camera_binding::QueryResult;
template struct e33_authored_binding::PortableResolverOps<StrongLeasePool<>>;
struct TestOps {
    bool owned=true,unavailable=false,corrupt=false,lose_after=false,throw_dispatch=false;
    unsigned dispatches=0,ownership_checks=0;
    bool context()const{return true;}
    bool owns(const PortableInputs&) {return owned && !(lose_after && ++ownership_checks>1);}
    struct Engine {
        TestOps& owner;const e33_portable_binding::Packet& packet;
        bool validate()const{return owner.owned;}
        void dispatch(void* args) {
            ++owner.dispatches;
            if(owner.throw_dispatch)throw std::runtime_error("dispatch interrupted");
            auto* bytes=static_cast<uint8_t*>(args);
            if(!owner.unavailable) {
                std::memcpy(bytes+40,packet.guid,16);
                int32_t sequence=71,parent=0;
                std::memcpy(bytes+56,&sequence,4);std::memcpy(bytes+60,&parent,4);
                if(owner.corrupt)bytes[40]^=1;
            }
        }
    };
    e33_portable_binding::Result query(e33_portable_binding::Frame& f,const e33_portable_binding::Packet& p) {
        assert(p.root.address==p.destination.address && p.tokens[2]==p.tokens[3]);
        Engine engine{*this,p};return f.query(engine,p);
    }
};
static PortableInputs inputs() {
    PortableInputs in{};
    in.target={1,1,0x10000};in.function={2,1,0x10008};
    in.root={3,1,0x10010};in.source={4,1,0x10018};
    in.target_token=1;in.function_token=2;in.root_token=3;in.source_token=4;return in;
}
int main() {
    const uint32_t guid[]{1,2,3,4};BindingValue out{};
    TestOps good;PortableResolver resolver;
    assert(resolver.resolve(good,inputs(),guid,out)==QueryResult::ok);
    assert(out.guid[0]==1 && out.guid[3]==4 && out.sequence_id==71 && out.resolve_parent_index==0);
    assert(resolver.resolve(good,inputs(),guid,out)==QueryResult::ok && good.dispatches==2);
    TestOps absent;absent.unavailable=true;PortableResolver empty;
    assert(empty.resolve(absent,inputs(),guid,out)==QueryResult::rejected && !empty.uncertain());
    absent.unavailable=false;assert(empty.resolve(absent,inputs(),guid,out)==QueryResult::ok);
    TestOps invalid;invalid.owned=false;PortableResolver denied;
    assert(denied.resolve(invalid,inputs(),guid,out)==QueryResult::rejected && invalid.dispatches==0);
    TestOps changed;changed.lose_after=true;PortableResolver tainted;
    assert(tainted.resolve(changed,inputs(),guid,out)==QueryResult::unknown && tainted.uncertain());
    assert(tainted.resolve(changed,inputs(),guid,out)==QueryResult::rejected && changed.dispatches==1);
    TestOps mismatch;mismatch.corrupt=true;PortableResolver bad;
    assert(bad.resolve(mismatch,inputs(),guid,out)==QueryResult::unknown && bad.uncertain());
    assert(bad.resolve(mismatch,inputs(),guid,out)==QueryResult::rejected && mismatch.dispatches==1);
    TestOps interrupted;interrupted.throw_dispatch=true;PortableResolver incomplete;
    try {incomplete.resolve(interrupted,inputs(),guid,out);assert(false);} catch(const std::runtime_error&) {}
    assert(incomplete.uncertain() && incomplete.resolve(interrupted,inputs(),guid,out)==QueryResult::rejected);
    assert(interrupted.dispatches==1);
}
