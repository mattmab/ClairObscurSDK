#pragma once
#include <cstddef>
#include <cstdint>
namespace e33_npc_presentation {
struct ConditionGraphEdge {uint64_t object=0,parent=0;};
// Bounded original-wrapper traversal, not a general UObject discovery API.
// Every edge must prove direct ownership before retention; cycles and shared
// aliases are rejected, never silently pruned into an incomplete target set.
template<class Ops> bool visit_owned_condition_graph(const ConditionGraphEdge* roots,size_t root_count,Ops& ops){
    if(!roots||!root_count||root_count>8)return false;
    ConditionGraphEdge pending[32]{};uint64_t seen[32]{};
    size_t count=root_count,head=0,visited=0;
    for(size_t i=0;i<root_count;++i)pending[i]=roots[i];
    while(head<count){
        const auto edge=pending[head++];
        if(edge.object<0x10000||edge.parent<0x10000)return false;
        for(size_t i=0;i<visited;++i)if(seen[i]==edge.object)return false;
        if(visited>=32||!ops.retain_exact_owned(edge.object,edge.parent))return false;
        seen[visited++]=edge.object;
        uint64_t children[8]{};size_t child_count=0;
        if(!ops.children(edge.object,children,child_count)||child_count>8||child_count>32-count)return false;
        for(size_t i=0;i<child_count;++i)pending[count++]={children[i],edge.object};
    }
    return visited!=0;
}
}
