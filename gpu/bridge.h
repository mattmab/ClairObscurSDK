#pragma once
#include "readback.h"
#include "image_readback.h"
#include <type_traits>
#include <deque>
namespace builder_gpu {
template<int Channel> class BridgeBase {
    using Reader=std::conditional_t<Channel==0,Readback,ImageReadback>;
    using RTV=void(STDMETHODCALLTYPE*)(ID3D12Device*,ID3D12Resource*,const D3D12_RENDER_TARGET_VIEW_DESC*,D3D12_CPU_DESCRIPTOR_HANDLE);
    using Barrier=void(STDMETHODCALLTYPE*)(ID3D12GraphicsCommandList*,UINT,const D3D12_RESOURCE_BARRIER*);
    using Targets=void(STDMETHODCALLTYPE*)(ID3D12GraphicsCommandList*,UINT,const D3D12_CPU_DESCRIPTOR_HANDLE*,BOOL,const D3D12_CPU_DESCRIPTOR_HANDLE*);
    using ClearRTV=void(STDMETHODCALLTYPE*)(ID3D12GraphicsCommandList*,D3D12_CPU_DESCRIPTOR_HANDLE,const FLOAT*,UINT,const D3D12_RECT*);
    using Draw=void(STDMETHODCALLTYPE*)(ID3D12GraphicsCommandList*,UINT,UINT,UINT,UINT);
    using DrawIndexed=void(STDMETHODCALLTYPE*)(ID3D12GraphicsCommandList*,UINT,UINT,UINT,INT,UINT);
    Draw draw_=nullptr;DrawIndexed indexed_=nullptr;
    std::unordered_map<ID3D12CommandList*,bool> bound_;
    using Reset=HRESULT(STDMETHODCALLTYPE*)(ID3D12GraphicsCommandList*,ID3D12CommandAllocator*,ID3D12PipelineState*);
    using Execute=void(STDMETHODCALLTYPE*)(ID3D12CommandQueue*,UINT,ID3D12CommandList*const*);
    struct Patch {void** slot=nullptr;void* original=nullptr;void* replacement=nullptr;};
    struct Recorded {D3D12_RESOURCE_STATES after=D3D12_RESOURCE_STATE_COMMON;bool ready=false;};
    inline static BridgeBase* instance_=nullptr;
    inline static thread_local bool internal_=false;
    std::array<Patch,8> patches_{};
    RTV rtv_=nullptr;Barrier barrier_=nullptr;Reset reset_=nullptr;Execute execute_=nullptr;
    Targets targets_=nullptr;ClearRTV clear_=nullptr;
    std::atomic<SIZE_T> rtv_handle_{0};std::atomic<UINT> rtv_stride_{0};
    std::mutex mutex_,submit_mutex_;
    std::unordered_map<ID3D12CommandList*,Recorded> recorded_;
    ComPtr<ID3D12Resource> target_;
    ComPtr<ID3D12Device> device_;
    std::unique_ptr<Reader> reader_;
    std::atomic<ID3D12Resource*> observed_{nullptr};
    std::atomic<bool> active_{false};
    std::atomic<uint32_t> error_{0},observed_format_{0};
    std::array<std::atomic<uint64_t>,12> diagnostics_{};
    UINT width_=0,height_=0,required_writes_=1,request_writes_=0;
    std::deque<uint64_t> requests_;UINT in_flight_=0;
    uint64_t requested_=0,submitted_=0,result_=0;
    float depth_=0;
    static bool change(Patch& p,void** slot,void* replacement) {
        p.slot=slot;p.original=*slot;p.replacement=replacement;
        DWORD old=0;if(!VirtualProtect(slot,sizeof(void*),PAGE_READWRITE,&old))return false;
        const bool ok=InterlockedCompareExchangePointer(slot,replacement,p.original)==p.original;
        DWORD ignored=0;VirtualProtect(slot,sizeof(void*),old,&ignored);return ok;
    }
    static void restore(Patch& p) {
        if(!p.slot)return;DWORD old=0;
        if(VirtualProtect(p.slot,sizeof(void*),PAGE_READWRITE,&old)) {InterlockedCompareExchangePointer(p.slot,p.original,p.replacement);DWORD ignored=0;VirtualProtect(p.slot,sizeof(void*),old,&ignored);}
        p.slot=nullptr;
    }
    static void STDMETHODCALLTYPE on_rtv(ID3D12Device* d,ID3D12Resource* resource,const D3D12_RENDER_TARGET_VIEW_DESC* desc,D3D12_CPU_DESCRIPTOR_HANDLE handle) {
        auto& s=*instance_;++s.diagnostics_[0];s.rtv_(d,resource,desc,handle);
        if(!s.active_||!resource)return;
        const auto r=resource->GetDesc();if(r.Width==s.width_&&r.Height==s.height_)s.observed_format_=uint32_t(r.Format);
        if(r.Width!=s.width_||r.Height!=s.height_||(Channel==0?r.Format!=DXGI_FORMAT_R32_FLOAT:(r.Format!=DXGI_FORMAT_B8G8R8A8_UNORM&&r.Format!=DXGI_FORMAT_R8G8B8A8_UNORM&&r.Format!=DXGI_FORMAT_B8G8R8A8_TYPELESS&&r.Format!=DXGI_FORMAT_R8G8B8A8_TYPELESS&&r.Format!=DXGI_FORMAT_B8G8R8A8_UNORM_SRGB&&r.Format!=DXGI_FORMAT_R8G8B8A8_UNORM_SRGB))||r.DepthOrArraySize!=1||r.MipLevels!=1||r.SampleDesc.Count!=1)return;
        std::lock_guard<std::mutex> lock(s.mutex_);
        if(s.target_&&s.target_.Get()!=resource){s.error_=2;return;}
        s.target_=resource;s.device_=d;s.rtv_handle_=handle.ptr;s.rtv_stride_=d->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_RTV);s.observed_=resource;
    }
    static void STDMETHODCALLTYPE on_targets(ID3D12GraphicsCommandList* list,UINT count,const D3D12_CPU_DESCRIPTOR_HANDLE* handles,BOOL contiguous,const D3D12_CPU_DESCRIPTOR_HANDLE* dsv) {
        auto& s=*instance_;++s.diagnostics_[8];
        if(s.active_&&s.observed_&&!internal_&&handles) {
            const auto handle=s.rtv_handle_.load();const auto stride=s.rtv_stride_.load();
            {std::lock_guard<std::mutex> lock(s.mutex_);s.bound_[list]=false;}
            for(UINT i=0;i<count;++i)if((contiguous?handles[0].ptr+SIZE_T(i)*stride:handles[i].ptr)==handle) {
                std::lock_guard<std::mutex> lock(s.mutex_);s.bound_[list]=true;s.recorded_[list].after=D3D12_RESOURCE_STATE_RENDER_TARGET;++s.diagnostics_[9];break;
            }
        }
        s.targets_(list,count,handles,contiguous,dsv);
    }
    static void STDMETHODCALLTYPE on_clear(ID3D12GraphicsCommandList* list,D3D12_CPU_DESCRIPTOR_HANDLE handle,const FLOAT* color,UINT count,const D3D12_RECT* rects) {
        auto& s=*instance_;++s.diagnostics_[10];
        if(s.active_&&s.observed_&&!internal_&&handle.ptr==s.rtv_handle_) {
            std::lock_guard<std::mutex> lock(s.mutex_);s.recorded_[list].after=D3D12_RESOURCE_STATE_RENDER_TARGET;++s.diagnostics_[11];
        }
        s.clear_(list,handle,color,count,rects);
    }
    static void mark_draw(ID3D12GraphicsCommandList* list) {
        auto& s=*instance_;if(!s.active_||!s.observed_||internal_)return;
        std::lock_guard<std::mutex> lock(s.mutex_);auto it=s.bound_.find(list);
        if(it!=s.bound_.end()&&it->second)s.recorded_[list]={D3D12_RESOURCE_STATE_RENDER_TARGET,true};
    }
    static void STDMETHODCALLTYPE on_draw(ID3D12GraphicsCommandList* list,UINT a,UINT b,UINT c,UINT d){mark_draw(list);instance_->draw_(list,a,b,c,d);}
    static void STDMETHODCALLTYPE on_indexed(ID3D12GraphicsCommandList* list,UINT a,UINT b,UINT c,INT d,UINT e){mark_draw(list);instance_->indexed_(list,a,b,c,d,e);}
    static HRESULT STDMETHODCALLTYPE on_reset(ID3D12GraphicsCommandList* list,ID3D12CommandAllocator* allocator,ID3D12PipelineState* pipeline) {
        auto& s=*instance_;
        if(s.active_&&!internal_){std::lock_guard<std::mutex> lock(s.mutex_);s.recorded_.erase(list);s.bound_.erase(list);}
        return s.reset_(list,allocator,pipeline);
    }
    static void STDMETHODCALLTYPE on_barrier(ID3D12GraphicsCommandList* list,UINT count,const D3D12_RESOURCE_BARRIER* barriers) {
        auto& s=*instance_;++s.diagnostics_[1];const auto observedTarget=s.observed_.load();
        if(s.active_&&observedTarget&&!internal_) {
            for(UINT i=0;i<count;++i) {
                const auto& r=barriers[i];
                if(r.Type!=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION||r.Transition.pResource!=observedTarget)continue;
                std::lock_guard<std::mutex> lock(s.mutex_);
                if(r.Flags!=D3D12_RESOURCE_BARRIER_FLAG_NONE||(r.Transition.Subresource!=0&&r.Transition.Subresource!=D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES)){s.error_=3;continue;}
                ++s.diagnostics_[2];s.diagnostics_[6]=r.Transition.StateBefore;s.diagnostics_[7]=r.Transition.StateAfter;
                auto& rec=s.recorded_[list];rec.after=r.Transition.StateAfter;
                constexpr auto writes=D3D12_RESOURCE_STATE_RENDER_TARGET|D3D12_RESOURCE_STATE_COPY_DEST|D3D12_RESOURCE_STATE_UNORDERED_ACCESS;
                if((r.Transition.StateBefore&writes)&&!(rec.after&writes))rec.ready=true;
                if(rec.after&writes)rec.ready=false;
            }
        }
        s.barrier_(list,count,barriers);
    }
    static void STDMETHODCALLTYPE on_execute(ID3D12CommandQueue* queue,UINT count,ID3D12CommandList*const* lists) {
        auto& s=*instance_;++s.diagnostics_[3];
        if(!s.active_||!s.observed_||internal_||queue->GetDesc().Type!=D3D12_COMMAND_LIST_TYPE_DIRECT){s.execute_(queue,count,lists);return;}
        std::lock_guard<std::mutex> submitLock(s.submit_mutex_);
        s.execute_(queue,count,lists);
        std::lock_guard<std::mutex> lock(s.mutex_);
        if(!s.active_)return;
        Recorded last{};bool touched=false;
        for(UINT i=0;i<count;++i){auto it=s.recorded_.find(lists[i]);if(it!=s.recorded_.end()){last=it->second;touched=true;s.recorded_.erase(it);}}
        if(touched)++s.diagnostics_[4];if(last.ready)++s.diagnostics_[5];
        if(!touched||!last.ready||s.requests_.empty()||s.error_)return;
        s.requested_=s.requests_.front();
        if(++s.request_writes_<s.required_writes_)return;
        internal_=true;
        if(!s.reader_)s.reader_=std::make_unique<Reader>();
        bool ok=s.reader_->init(s.device_.Get(),queue);
        if(ok)ok=s.reader_->submit(s.target_.Get(),last.after,s.width_/2,s.height_/2,s.requested_,s.execute_);
        internal_=false;
        if(ok){s.submitted_=s.requested_;s.requests_.pop_front();s.request_writes_=0;}else s.error_=4;
    }
public:
    bool start(UINT width,UINT height,UINT requiredWrites=1) {
        if(active_)return true;
        {std::lock_guard<std::mutex> lock(mutex_);if(reader_){float ignored;while(reader_->poll(ignored)){}if(!reader_->idle()){error_=5;return false;}reader_.reset();target_.Reset();device_.Reset();}}
        width_=width;height_=height;required_writes_=requiredWrites;request_writes_=0;error_=0;requested_=submitted_=result_=0;requests_.clear();in_flight_=0;instance_=this;
        ComPtr<ID3D12Device> device;ComPtr<ID3D12CommandQueue> queue;ComPtr<ID3D12CommandAllocator> allocator;ComPtr<ID3D12GraphicsCommandList> list;
        if(FAILED(D3D12CreateDevice(nullptr,D3D_FEATURE_LEVEL_11_0,IID_PPV_ARGS(&device)))){error_=1;return false;}
        D3D12_COMMAND_QUEUE_DESC desc{};
        if(FAILED(device->CreateCommandQueue(&desc,IID_PPV_ARGS(&queue)))||FAILED(device->CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT,IID_PPV_ARGS(&allocator)))||FAILED(device->CreateCommandList(0,D3D12_COMMAND_LIST_TYPE_DIRECT,allocator.Get(),nullptr,IID_PPV_ARGS(&list)))){error_=1;return false;}
        list->Close();
        auto dv=*reinterpret_cast<void***>(device.Get()),qv=*reinterpret_cast<void***>(queue.Get()),lv=*reinterpret_cast<void***>(list.Get());
        // COM ABI slots are fixed by d3d12.h. Publish originals before installing.
        draw_=reinterpret_cast<Draw>(lv[12]);indexed_=reinterpret_cast<DrawIndexed>(lv[13]);
        targets_=reinterpret_cast<Targets>(lv[46]);clear_=reinterpret_cast<ClearRTV>(lv[48]);
        rtv_=reinterpret_cast<RTV>(dv[20]);barrier_=reinterpret_cast<Barrier>(lv[26]);reset_=reinterpret_cast<Reset>(lv[10]);execute_=reinterpret_cast<Execute>(qv[10]);
        if(!change(patches_[0],dv+20,reinterpret_cast<void*>(&on_rtv))||!change(patches_[1],lv+26,reinterpret_cast<void*>(&on_barrier))||!change(patches_[2],lv+10,reinterpret_cast<void*>(&on_reset))||!change(patches_[3],qv+10,reinterpret_cast<void*>(&on_execute))||!change(patches_[4],lv+46,reinterpret_cast<void*>(&on_targets))||!change(patches_[5],lv+48,reinterpret_cast<void*>(&on_clear))||!change(patches_[6],lv+12,reinterpret_cast<void*>(&on_draw))||!change(patches_[7],lv+13,reinterpret_cast<void*>(&on_indexed))){for(auto& p:patches_)restore(p);error_=1;return false;}
        active_=true;return true;
    }
    void diagnostics(uint64_t* out)const{for(size_t i=0;i<12;++i)out[i]=diagnostics_[i].load();}
    bool ready()const{return observed_&&!error_;}
    uint32_t observed_format()const{return observed_format_;}
    uint32_t error()const{return error_;}
    bool arm(uint64_t request) {
        std::unique_lock<std::mutex> lock(mutex_,std::try_to_lock);if(!lock||!ready()||in_flight_>=3)return false;
        requests_.push_back(request);++in_flight_;return true;
    }
    uint64_t poll(float& sampleDepth) {
        std::unique_lock<std::mutex> lock(mutex_,std::try_to_lock);if(!lock||!reader_)return 0;
        const auto id=reader_->poll(sampleDepth);
        if(id){result_=id;depth_=sampleDepth;if(in_flight_)--in_flight_;}return id;
    }
    uint64_t poll_image(std::vector<uint8_t>& rgb) {
        std::unique_lock<std::mutex> lock(mutex_,std::try_to_lock);if(!lock||!reader_)return 0;
        if constexpr(Channel==1){const auto id=reader_->poll_image(rgb);if(id&&in_flight_)--in_flight_;return id;}
        return 0;
    }
    bool stop() {
        active_=false;
        std::lock_guard<std::mutex> lock(mutex_);
        observed_=nullptr;
        for(auto& p:patches_)restore(p);
        recorded_.clear();bound_.clear();requests_.clear();in_flight_=0;requested_=submitted_=result_=0;
        if(reader_) {float ignored;while(reader_->poll(ignored)){}if(!reader_->idle())return true;}
        reader_.reset();target_.Reset();device_.Reset();return true;
    }
};
using Bridge=BridgeBase<0>;
using ImageBridge=BridgeBase<1>;
}

