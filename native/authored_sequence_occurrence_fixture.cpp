#include "authored_sequence_occurrence.h"
#include <cassert>
#include <vector>
struct Graph {
    std::array<std::vector<unsigned>,128> edges;
    bool live=true,changing=false;unsigned root_reads=0;
    bool context()const{return live;}
    bool valid(unsigned value)const{return value>0 && value<128;}
    bool same(unsigned a,unsigned b)const{return a==b;}
    template<class Sink> bool children(unsigned node,Sink sink) {
        if(node==1 && ++root_reads==2 && changing)edges[1].push_back(4);
        for(auto child:edges[node])if(!sink(child))return false;
        return true;
    }
};
int main() {
    e33_authored_occurrence::Proof<unsigned> proof;
    Graph single;single.edges[1]={2,3};single.edges[2]={4};single.edges[3]={5};
    assert(proof.unique(single,1,4));
    assert(proof.unique(single,1,1));
    assert(!proof.unique(single,1,6));
    Graph repeat;repeat.edges[1]={2,3};repeat.edges[2]={4};repeat.edges[3]={4};
    assert(!proof.unique(repeat,1,4));
    Graph duplicate;duplicate.edges[1]={4,4};assert(!proof.unique(duplicate,1,4));
    Graph cycle;cycle.edges[1]={2,4};cycle.edges[2]={3};cycle.edges[3]={2};
    assert(!proof.unique(cycle,1,4));assert(!proof.unique(cycle,1,1));
    Graph changed;changed.edges[1]={2};changed.edges[2]={4};changed.changing=true;
    assert(!proof.unique(changed,1,4));
    Graph lost;lost.live=false;assert(!proof.unique(lost,1,1));
    Graph overflow;for(unsigned i=0;i<4097;++i)overflow.edges[1].push_back(2);
    assert(!proof.unique(overflow,1,2));
}
