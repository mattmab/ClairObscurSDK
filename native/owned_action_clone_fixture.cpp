#include "owned_action_clone.h"
#include <cassert>
#include <vector>
#include <stdexcept>
using namespace e33_action_clone;
struct Ops {
    bool profile=true,owned=true,sources_unchanged=true,current=true,retired=false;
    int fail_source=-1,unknown_clone=-1,throw_copy=-1;
    unsigned constructions=0,copies=0,links=0,dispatches=0;
    Result dispatch=Result::returned,release_result=Result::returned;
    std::vector<uint64_t> released;
    bool null(uint64_t id) {return !id;}
    bool admit_complete_simon_profile() {return profile;}
    Result acquire_context(uint64_t& id,uint64_t& token) {id=100;token=100;return Result::returned;}
    Result acquire_source(unsigned i,uint64_t& id,uint64_t& token) {
        if(int(i)==fail_source)return Result::not_dispatched;
        id=i+1;token=i+1;return Result::returned;
    }
    Result construct_owned(Node node,uint64_t outer,uint64_t& id,uint64_t& token) {
        assert(outer==(node.source ? 1000U : 100U));
        id=1000+node.source;token=id;++constructions;
        return int(node.source)==unknown_clone ? Result::unknown : Result::returned;
    }
    bool prove_owned(Node node,uint64_t source,uint64_t outer,uint64_t id,uint64_t token) {
        return owned && source==node.source+1 && id==1000+node.source && token==id && outer==(node.source ? 1000U : 100U);
    }
    Result copy_complete_profile(Node node,uint64_t source,uint64_t destination) {
        assert(source==node.source+1 && destination==1000+node.source);++copies;
        if(int(node.source)==throw_copy)throw std::runtime_error("Unknown engine copy");
        return Result::returned;
    }
    template<class Holds> Result link_complete_simon_wrappers(const Holds& h) {
        assert(h[12].identity==1000);
        for(unsigned i=0;i<10;++i) {
            const auto selected=i<5 ? h[13+i].identity : h[2+i].identity;
            assert(selected==(i<5 ? 1001U+i : i+2));
        }
        ++links;return Result::returned;
    }
    template<class Holds> bool verify_complete_clone_and_unchanged_sources(const Holds&) {return sources_unchanged;}
    template<class Holds> bool current_clone_context(const Holds&) {return current;}
    Result dispatch_exact_owned_root(uint64_t root) {assert(root==1000);++dispatches;return dispatch;}
    bool prove_owned_execution_retired(uint64_t root) {assert(root==1000);return retired;}
    Result release(uint64_t id,uint64_t token) {assert(id==token);if(release_result==Result::returned)released.push_back(id);return release_result;}
};
int main() {
    {SimonCloneOwner<uint64_t> owner;Ops o;assert(owner.open(o));assert(o.constructions==6 && o.copies==6 && o.links==1);
     assert(!owner.open(o));assert(owner.execute(o));assert(!owner.execute(o));assert(!owner.close(o));assert(o.released.empty());
     o.retired=true;assert(owner.close(o));assert(o.released.size()==18);assert(o.released.front()==1005 && o.released.back()==100);}
    {SimonCloneOwner<uint64_t> owner;Ops o;o.profile=false;assert(!owner.open(o));assert(!o.constructions);assert(owner.close(o));}
    {SimonCloneOwner<uint64_t> owner;Ops o;o.fail_source=4;assert(!owner.open(o));assert(!owner.quarantined());assert(owner.close(o));assert(o.released.size()==5);}
    {SimonCloneOwner<uint64_t> owner;Ops o;o.unknown_clone=2;assert(!owner.open(o));assert(owner.quarantined());assert(!owner.close(o));assert(o.released.empty());}
    {SimonCloneOwner<uint64_t> owner;Ops o;o.owned=false;assert(!owner.open(o));assert(owner.quarantined());assert(!owner.close(o));}
    {SimonCloneOwner<uint64_t> owner;Ops o;o.throw_copy=3;try {owner.open(o);assert(false);}catch(const std::runtime_error&){}
     assert(owner.quarantined());assert(!owner.close(o));}
    {SimonCloneOwner<uint64_t> owner;Ops o;o.sources_unchanged=false;assert(!owner.open(o));assert(owner.quarantined());assert(!owner.close(o));}
    {SimonCloneOwner<uint64_t> owner;Ops o;assert(owner.open(o));o.current=false;assert(!owner.execute(o));assert(!o.dispatches);assert(owner.close(o));}
    {SimonCloneOwner<uint64_t> owner;Ops o;assert(owner.open(o));o.dispatch=Result::unknown;assert(!owner.execute(o));assert(owner.quarantined());assert(!owner.execute(o));assert(o.dispatches==1);assert(!owner.close(o));}
    {SimonCloneOwner<uint64_t> owner;Ops o;assert(owner.open(o));o.dispatch=Result::not_dispatched;assert(!owner.execute(o));assert(!owner.execute(o));assert(o.dispatches==1);assert(owner.close(o));}
    {SimonCloneOwner<uint64_t> owner;Ops o;assert(owner.open(o));o.release_result=Result::not_dispatched;assert(!owner.close(o));assert(!owner.quarantined());o.release_result=Result::returned;assert(owner.close(o));}
    {SimonCloneOwner<uint64_t> owner;Ops o;assert(owner.open(o));o.release_result=Result::unknown;assert(!owner.close(o));assert(owner.quarantined());assert(!owner.close(o));}
}
