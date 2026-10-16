#pragma once
#include <windows.h>
#include <d3d12.h>
#include <dxgi1_6.h>
#include <wrl/client.h>
#include <array>
#include <atomic>
#include <mutex>
#include <unordered_map>
#include <cmath>
#include <cstdint>
#include <memory>
#include <cstring>
namespace builder_gpu {
using Microsoft::WRL::ComPtr;
// Readback owns its buffers until the fence completes. No wait, flush, event,
// or Map of an unfinished GPU write is used by the picker.
class Readback {
    struct Slot {
        ComPtr<ID3D12CommandAllocator> allocator;
        ComPtr<ID3D12GraphicsCommandList> list;
        ComPtr<ID3D12Resource> buffer;
        uint64_t fence=0,request=0;
    };
    std::array<Slot,3> slots_;
    ComPtr<ID3D12Device> device_;
    ComPtr<ID3D12CommandQueue> queue_;
    ComPtr<ID3D12Fence> fence_;
    uint64_t sequence_=0;
public:
    bool init(ID3D12Device* device,ID3D12CommandQueue* queue) {
        if(device_)return device_.Get()==device&&queue_.Get()==queue;
        if(!device||!queue||queue->GetDesc().Type!=D3D12_COMMAND_LIST_TYPE_DIRECT)return false;
        device_=device;queue_=queue;
        if(FAILED(device->CreateFence(0,D3D12_FENCE_FLAG_NONE,IID_PPV_ARGS(&fence_))))return false;
        for(auto& s:slots_) {
            if(FAILED(device->CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT,IID_PPV_ARGS(&s.allocator))))return false;
            if(FAILED(device->CreateCommandList(0,D3D12_COMMAND_LIST_TYPE_DIRECT,s.allocator.Get(),nullptr,IID_PPV_ARGS(&s.list)))||FAILED(s.list->Close()))return false;
            D3D12_HEAP_PROPERTIES heap{};heap.Type=D3D12_HEAP_TYPE_READBACK;
            D3D12_RESOURCE_DESC desc{};desc.Dimension=D3D12_RESOURCE_DIMENSION_BUFFER;desc.Width=256;desc.Height=1;desc.DepthOrArraySize=1;desc.MipLevels=1;desc.SampleDesc.Count=1;desc.Layout=D3D12_TEXTURE_LAYOUT_ROW_MAJOR;
            if(FAILED(device->CreateCommittedResource(&heap,D3D12_HEAP_FLAG_NONE,&desc,D3D12_RESOURCE_STATE_COPY_DEST,nullptr,IID_PPV_ARGS(&s.buffer))))return false;
        }
        return true;
    }
    template<class Submit> bool submit(ID3D12Resource* source,D3D12_RESOURCE_STATES state,UINT x,UINT y,uint64_t request,Submit execute) {
        if(!fence_||!source||!request)return false;
        const auto desc=source->GetDesc();
        if(desc.Dimension!=D3D12_RESOURCE_DIMENSION_TEXTURE2D||desc.Format!=DXGI_FORMAT_R32_FLOAT||desc.SampleDesc.Count!=1||desc.DepthOrArraySize!=1||x>=desc.Width||y>=desc.Height)return false;
        Slot* s=nullptr;for(auto& slot:slots_)if(!slot.request){s=&slot;break;}if(!s)return false;
        if(FAILED(s->allocator->Reset())||FAILED(s->list->Reset(s->allocator.Get(),nullptr)))return false;
        D3D12_RESOURCE_BARRIER barrier{};barrier.Type=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;barrier.Transition.pResource=source;barrier.Transition.Subresource=0;barrier.Transition.StateBefore=state;barrier.Transition.StateAfter=D3D12_RESOURCE_STATE_COPY_SOURCE;
        if(state!=D3D12_RESOURCE_STATE_COPY_SOURCE)s->list->ResourceBarrier(1,&barrier);
        D3D12_TEXTURE_COPY_LOCATION src{};src.pResource=source;src.Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX;
        D3D12_TEXTURE_COPY_LOCATION dst{};dst.pResource=s->buffer.Get();dst.Type=D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT;dst.PlacedFootprint.Footprint={DXGI_FORMAT_R32_FLOAT,1,1,1,256};
        D3D12_BOX box{x,y,0,x+1,y+1,1};s->list->CopyTextureRegion(&dst,0,0,0,&src,&box);
        if(state!=D3D12_RESOURCE_STATE_COPY_SOURCE){std::swap(barrier.Transition.StateBefore,barrier.Transition.StateAfter);s->list->ResourceBarrier(1,&barrier);}
        if(FAILED(s->list->Close()))return false;
        ID3D12CommandList* lists[]={s->list.Get()};execute(queue_.Get(),1,lists);
        s->request=request;s->fence=++sequence_;
        if(FAILED(queue_->Signal(fence_.Get(),s->fence)))return false;
        return true;
    }
    // Returns zero when not ready. The caller keeps flying instead of waiting.
    uint64_t poll(float& sampleDepth) {
        if(!fence_)return 0;
        const auto completed=fence_->GetCompletedValue();if(completed==UINT64_MAX)return 0;
        for(auto& s:slots_)if(s.request&&s.fence<=completed) {
            void* bytes=nullptr;D3D12_RANGE range{0,sizeof(float)};
            if(FAILED(s.buffer->Map(0,&range,&bytes)))return 0;
            std::memcpy(&sampleDepth,bytes,sizeof(float));D3D12_RANGE written{0,0};s.buffer->Unmap(0,&written);
            const auto request=s.request;s.request=0;return request;
        }
        return 0;
    }
    bool idle()const {for(const auto& s:slots_)if(s.request)return false;return true;}
};
}


