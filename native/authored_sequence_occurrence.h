#pragma once
#include <array>
#include <cstdint>

// Research-only, bounded graph attestation. Ops::children must enumerate every
// native SubSequence reference, including repeated source occurrences, while
// checking track/section ownership and layout. It must not deduplicate distinct
// sections that happen to refer to the same child. Two identical full reads
// are required; duplicate edges are meaningful. A cycle or any ambiguity
// rejects. The owner supplies persistent storage to avoid a large game stack.
namespace e33_authored_occurrence {
template<class Identity> struct Snapshot {
    struct Edge {uint16_t parent=0,child=0;};
    std::array<Identity,128> nodes{};
    std::array<Edge,4096> edges{};
    uint16_t nodes_count=0,edge_count=0;
};
template<class Identity> class Proof {
    Snapshot<Identity> first_{},second_{};
    template<class Ops> static bool capture(Ops& ops,const Identity& root,Snapshot<Identity>& out) {
        out={};if(!ops.context() || !ops.valid(root))return false;
        out.nodes[0]=root;out.nodes_count=1;
        for(uint16_t i=0;i<out.nodes_count;++i) {
            if(!ops.context() || !ops.valid(out.nodes[i]))return false;
            bool valid=true;
            const auto child=[&](const Identity& id) {
                if(!valid || !ops.valid(id) || out.edge_count==out.edges.size()){valid=false;return false;}
                uint16_t index=0;
                for(;index<out.nodes_count;++index)if(ops.same(out.nodes[index],id))break;
                if(index==out.nodes_count) {
                    if(out.nodes_count==out.nodes.size()){valid=false;return false;}
                    out.nodes[out.nodes_count++]=id;
                }
                out.edges[out.edge_count++]={i,index};return true;
            };
            if(!ops.children(out.nodes[i],child) || !valid || !ops.valid(out.nodes[i]))return false;
        }
        return ops.context();
    }
    template<class Ops> static bool equal(Ops& ops,const Snapshot<Identity>& a,const Snapshot<Identity>& b) {
        if(a.nodes_count!=b.nodes_count || a.edge_count!=b.edge_count)return false;
        for(uint16_t i=0;i<a.nodes_count;++i)if(!ops.same(a.nodes[i],b.nodes[i]))return false;
        for(uint16_t i=0;i<a.edge_count;++i)
            if(a.edges[i].parent!=b.edges[i].parent || a.edges[i].child!=b.edges[i].child)return false;
        return true;
    }
    static bool count(const Snapshot<Identity>& graph,uint16_t node,uint16_t target_index,
                      std::array<uint8_t,128>& states,std::array<uint8_t,128>& counts) {
        if(states[node]==1)return false;
        if(states[node]==2)return true;
        states[node]=1;unsigned total=0;
        for(uint16_t e=0;e<graph.edge_count;++e)if(graph.edges[e].parent==node) {
            const auto child=graph.edges[e].child;
            if(!count(graph,child,target_index,states,counts))return false;
            total+=counts[child];if(total>2)total=2;
        }
        counts[node]=node==target_index ? 1 : static_cast<uint8_t>(total);
        states[node]=2;return true;
    }
public:
    template<class Ops> bool unique(Ops& ops,const Identity& root,const Identity& source) {
        if(!ops.valid(source) || !capture(ops,root,first_) || !capture(ops,root,second_) ||
           !equal(ops,first_,second_))return false;
        uint16_t target_index=0;
        for(;target_index<first_.nodes_count;++target_index)if(ops.same(first_.nodes[target_index],source))break;
        if(target_index==first_.nodes_count)return false;
        std::array<uint8_t,128> states{},counts{};
        if(!count(first_,0,target_index,states,counts) || counts[0]!=1)return false;
        for(uint16_t i=0;i<first_.nodes_count;++i)if(!ops.valid(first_.nodes[i]))return false;
        return ops.context() && ops.valid(root) && ops.valid(source);
    }
};
}
