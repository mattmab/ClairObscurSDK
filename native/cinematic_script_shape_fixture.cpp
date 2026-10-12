#include "cinematic_script_shape.h"
#include "cinematic_track_shape.h"
#include "cinematic_callback_shapes.h"
#include <array>
#include <cstring>
#include <cassert>
#include <iostream>
template<size_t N,size_t M>
void reject_every_changed_byte(const uint8_t (&expected)[N],const uint32_t (&offsets)[M]) {
    std::array<uint8_t,N> data{};
    std::memcpy(data.data(),expected,N);
    uint64_t values[M]{};
    for(size_t i=0;i<M;++i) {
        values[i]=0x100000+i*16;
        std::memcpy(data.data()+offsets[i],&values[i],8);
    }
    auto read=[&](uint64_t address,void* output,size_t size) {
        if(address<0x3000 || address-0x3000>N || size>N-(address-0x3000)) return false;
        std::memcpy(output,data.data()+address-0x3000,size);return true;};
    assert(e33_cinematic::exact_script_shape(read,0x3000,expected,offsets,values));
    for(size_t i=0;i<N;++i) {
        data[i]^=1;
        assert(!e33_cinematic::exact_script_shape(read,0x3000,expected,offsets,values));
        data[i]^=1;
    }
}
int main() {
    using namespace e33_cinematic;
    uint8_t expected[20]={0x5f}; std::array<uint8_t,20> data{};data[0]=0x5f;
    const uint32_t positions[]={2,11};uint64_t values[]={0x123456,0x56789};
    std::memcpy(data.data()+2,&values[0],8);std::memcpy(data.data()+11,&values[1],8);
    auto read=[&](uint64_t address,void* output,size_t size) {
        if(address<0x1000 || address-0x1000>data.size() || size>data.size()-(address-0x1000)) return false;
        std::memcpy(output,data.data()+address-0x1000,size);return true;};
    assert(exact_script_shape(read,0x1000,expected,positions,values));
    data[19]=1;assert(!exact_script_shape(read,0x1000,expected,positions,values));data[19]=0;
    ++values[1];assert(!exact_script_shape(read,0x1000,expected,positions,values));--values[1];
    uint32_t overlap[]={2,5};assert(!exact_script_shape(read,0x1000,expected,overlap,values));
    uint32_t outside[]={2,18};assert(!exact_script_shape(read,0x1000,expected,outside,values));
    assert(!exact_script_shape(read,UINT64_MAX-2,expected,positions,values));
    values[0]=0;assert(!exact_script_shape(read,0x1000,expected,positions,values));
    std::array<uint8_t,690> graph{};
    std::memcpy(graph.data(),widget_graph_bytes,graph.size());
    uint64_t bindings[52]{};
    for(size_t i=0;i<52;++i) {
        bindings[i]=0x100000+uint64_t(widget_binding_values[i])*16;
        std::memcpy(graph.data()+widget_binding_offsets[i],&bindings[i],8);
    }
    auto graph_read=[&](uint64_t address,void* output,size_t size) {
        if(address<0x2000 || address-0x2000>graph.size() || size>graph.size()-(address-0x2000)) return false;
        std::memcpy(output,graph.data()+address-0x2000,size);return true;};
    assert(exact_script_shape(graph_read,0x2000,widget_graph_bytes,widget_binding_offsets,bindings));
    // Every literal and rebound operand byte remains constrained.
    for(size_t i=0;i<graph.size();++i) {
        graph[i]^=1;
        assert(!exact_script_shape(graph_read,0x2000,widget_graph_bytes,widget_binding_offsets,bindings));
        graph[i]^=1;
    }
    reject_every_changed_byte(widget_register_bytes,widget_register_offsets);
    reject_every_changed_byte(widget_unregister_bytes,widget_unregister_offsets);
    reject_every_changed_byte(widget_controls_null_prefix_bytes,widget_controls_null_prefix_offsets);
    std::cout<<"Cinematic exact script guards passed (690 graph + 205 callback/branch byte mutations rejected)\n";
}
