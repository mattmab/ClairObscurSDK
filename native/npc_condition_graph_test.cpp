#include "npc_condition_graph.h"
#include <cassert>
#include <iostream>
#include <map>
#include <vector>
using namespace e33_npc_presentation;
struct Node {uint64_t parent;std::vector<uint64_t> children;bool admitted=true;};
struct GraphOps {
    std::map<uint64_t,Node> nodes;
    std::vector<uint64_t> retained;
    bool child_failure=false;
    bool retain_exact_owned(uint64_t object,uint64_t parent){
        const auto i=nodes.find(object);
        if(i==nodes.end()||!i->second.admitted||i->second.parent!=parent)return false;
        retained.push_back(object);return true;
    }
    bool children(uint64_t object,uint64_t* out,size_t& count){
        if(child_failure)return false;
        const auto& children=nodes.at(object).children;
        count=children.size();
        if(count<=8)for(size_t i=0;i<count;++i)out[i]=children[i];
        return true;
    }
};
static GraphOps original(){
    return {{{0x20000,{0x10000,{0x30000,0x40000}}},
             {0x30000,{0x20000,{}}},{0x40000,{0x20000,{0x50000}}},
             {0x50000,{0x40000,{}}}}};
}
int main(){
    const ConditionGraphEdge root{0x20000,0x10000};unsigned checks=0;
    auto run=[&](GraphOps& ops,const ConditionGraphEdge* roots,size_t count){
        ++checks;return visit_owned_condition_graph(roots,count,ops);
    };
    auto good=original();assert(run(good,&root,1)&&good.retained.size()==4);
    good=original();assert(!run(good,nullptr,1)&&good.retained.empty());
    assert(!run(good,&root,0));assert(!run(good,&root,9));
    auto bad=original();bad.nodes[0x30000].parent=0xdeadbeef;
    assert(!run(bad,&root,1)); // borrowed condition must never be retained
    bad=original();bad.nodes[0x30000].admitted=false;assert(!run(bad,&root,1));
    bad=original();bad.nodes.erase(0x30000);assert(!run(bad,&root,1));
    bad=original();bad.nodes[0x40000].children={0x20000};assert(!run(bad,&root,1)); // cycle
    bad=original();bad.nodes[0x20000].children={0x30000,0x30000};assert(!run(bad,&root,1));
    bad=original();bad.nodes[0x20000].children={0};assert(!run(bad,&root,1));
    bad=original();bad.child_failure=true;assert(!run(bad,&root,1));
    bad=original();bad.nodes[0x20000].children.resize(9,0x30000);assert(!run(bad,&root,1));
    ConditionGraphEdge duplicates[]={root,root};bad=original();assert(!run(bad,duplicates,2));
    ConditionGraphEdge invalid{0xffff,0x10000};bad=original();assert(!run(bad,&invalid,1));
    invalid={0x20000,0};assert(!run(bad,&invalid,1));
    GraphOps deep;
    for(uint64_t i=0;i<33;++i)deep.nodes[0x20000+i*0x10000]={0x10000+i*0x10000,
        i<32?std::vector<uint64_t>{0x30000+i*0x10000}:std::vector<uint64_t>{}};
    assert(!run(deep,&root,1)&&deep.retained.size()==32);
    deep.nodes[0x210000].children.clear();deep.retained.clear();
    assert(run(deep,&root,1)&&deep.retained.size()==32);
    std::cout<<checks<<" condition graph checks passed\n";
}
