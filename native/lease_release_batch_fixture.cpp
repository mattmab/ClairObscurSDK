#include "lease_release_batch_runtime.h"
#include <map>
#include <set>
#include <vector>
#include <cassert>
using namespace e33_lease_batch;
struct Ops {
    std::set<uint64_t> tokens,protected_tokens;std::map<uint64_t,uint32_t> effects;std::vector<uint64_t> calls;
    uint32_t admit(uint64_t token)const{return !tokens.count(token)?402:protected_tokens.count(token)?403:0;}
    uint32_t release(uint64_t token){calls.push_back(token);auto error=effects[token];if(!error)tokens.erase(token);return error;}
    uint32_t active()const{return uint32_t(tokens.size());}
};
static Packet make(Ops& ops,unsigned count){Packet p{};p.version=1;p.count=count;
    for(unsigned i=0;i<count;++i){p.rows[i].token=i+1;ops.tokens.insert(i+1);}return p;}
int main(){
    Ops ops;auto p=make(ops,128);run(p,ops);assert(!p.error&&p.completed==128&&p.active==0&&ops.calls.size()==128);
    ops=Ops{};p=make(ops,3);ops.protected_tokens.insert(2);run(p,ops);assert(p.error==403&&p.failed==2&&!p.completed&&ops.calls.empty()&&ops.tokens.size()==3);
    ops=Ops{};p=make(ops,3);ops.effects[2]=407;run(p,ops);assert(!p.error&&p.completed==3&&p.rows[1].outcome==Deferred&&ops.tokens==std::set<uint64_t>{2});
    ops=Ops{};p=make(ops,3);ops.effects[2]=408;run(p,ops);assert(p.error==408&&p.completed==2&&p.rows[0].outcome==Released&&p.rows[1].outcome==Unknown&&p.rows[2].outcome==NotDispatched);
    assert((ops.calls==std::vector<uint64_t>{1,2}));
    ops=Ops{};p=make(ops,3);p.rows[1].token=p.rows[0].token;run(p,ops);assert(p.error==3910&&ops.calls.empty());
    ops=Ops{};p=make(ops,3);ops.effects[2]=409;run(p,ops);assert(p.error==409&&p.rows[1].outcome==Rejected&&p.rows[2].outcome==NotDispatched);
    return 0;
}
