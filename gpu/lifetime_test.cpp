#include "bridge.h"
#include <d3dcompiler.h>
#include <cstdio>
#include <cassert>
using namespace builder_gpu;
int main(){
 Bridge bridge;assert(bridge.start(257,259));
 ComPtr<ID3D12Device> device;HRESULT hr=D3D12CreateDevice(nullptr,D3D_FEATURE_LEVEL_11_0,IID_PPV_ARGS(&device));if(FAILED(hr)){printf("device %lx\n",hr);return 2;}
 D3D12_COMMAND_QUEUE_DESC qd{};ComPtr<ID3D12CommandQueue> queue;assert(SUCCEEDED(device->CreateCommandQueue(&qd,IID_PPV_ARGS(&queue))));
 ComPtr<ID3D12CommandAllocator> allocator;ComPtr<ID3D12GraphicsCommandList> list;assert(SUCCEEDED(device->CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT,IID_PPV_ARGS(&allocator))));assert(SUCCEEDED(device->CreateCommandList(0,D3D12_COMMAND_LIST_TYPE_DIRECT,allocator.Get(),nullptr,IID_PPV_ARGS(&list))));
 D3D12_HEAP_PROPERTIES heap{};heap.Type=D3D12_HEAP_TYPE_DEFAULT;D3D12_RESOURCE_DESC desc{};desc.Dimension=D3D12_RESOURCE_DIMENSION_TEXTURE2D;desc.Width=257;desc.Height=259;desc.DepthOrArraySize=1;desc.MipLevels=1;desc.Format=DXGI_FORMAT_R32_FLOAT;desc.SampleDesc.Count=1;desc.Flags=D3D12_RESOURCE_FLAG_ALLOW_RENDER_TARGET;
 D3D12_CLEAR_VALUE clear{};clear.Format=desc.Format;clear.Color[0]=7;ComPtr<ID3D12Resource> target;assert(SUCCEEDED(device->CreateCommittedResource(&heap,D3D12_HEAP_FLAG_NONE,&desc,D3D12_RESOURCE_STATE_RENDER_TARGET,&clear,IID_PPV_ARGS(&target))));
 D3D12_DESCRIPTOR_HEAP_DESC hd{};hd.Type=D3D12_DESCRIPTOR_HEAP_TYPE_RTV;hd.NumDescriptors=1;ComPtr<ID3D12DescriptorHeap> descriptors;assert(SUCCEEDED(device->CreateDescriptorHeap(&hd,IID_PPV_ARGS(&descriptors))));auto rtv=descriptors->GetCPUDescriptorHandleForHeapStart();device->CreateRenderTargetView(target.Get(),nullptr,rtv);
 D3D12_ROOT_SIGNATURE_DESC rs{};rs.Flags=D3D12_ROOT_SIGNATURE_FLAG_ALLOW_INPUT_ASSEMBLER_INPUT_LAYOUT;ComPtr<ID3DBlob> blob,error;assert(SUCCEEDED(D3D12SerializeRootSignature(&rs,D3D_ROOT_SIGNATURE_VERSION_1,&blob,&error)));ComPtr<ID3D12RootSignature> root;assert(SUCCEEDED(device->CreateRootSignature(0,blob->GetBufferPointer(),blob->GetBufferSize(),IID_PPV_ARGS(&root))));
 const char shader[]="float4 vs(uint id:SV_VertexID):SV_Position {float2 v[3]={float2(-.8,-.8),float2(0,.8),float2(.8,-.8)};return float4(v[id],.5,1);} float ps():SV_Target{return 42;}";ComPtr<ID3DBlob> vs,ps;assert(SUCCEEDED(D3DCompile(shader,sizeof(shader),nullptr,nullptr,nullptr,"vs","vs_5_0",0,0,&vs,&error)));assert(SUCCEEDED(D3DCompile(shader,sizeof(shader),nullptr,nullptr,nullptr,"ps","ps_5_0",0,0,&ps,&error)));
 D3D12_GRAPHICS_PIPELINE_STATE_DESC pd{};pd.pRootSignature=root.Get();pd.VS={vs->GetBufferPointer(),vs->GetBufferSize()};pd.PS={ps->GetBufferPointer(),ps->GetBufferSize()};pd.BlendState.RenderTarget[0].RenderTargetWriteMask=D3D12_COLOR_WRITE_ENABLE_ALL;pd.SampleMask=UINT_MAX;pd.RasterizerState.FillMode=D3D12_FILL_MODE_SOLID;pd.RasterizerState.CullMode=D3D12_CULL_MODE_NONE;pd.RasterizerState.DepthClipEnable=TRUE;pd.DepthStencilState.DepthEnable=FALSE;pd.DepthStencilState.DepthFunc=D3D12_COMPARISON_FUNC_ALWAYS;pd.PrimitiveTopologyType=D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE;pd.NumRenderTargets=1;pd.RTVFormats[0]=desc.Format;pd.SampleDesc.Count=1;ComPtr<ID3D12PipelineState> pipeline;assert(SUCCEEDED(device->CreateGraphicsPipelineState(&pd,IID_PPV_ARGS(&pipeline))));
 list->SetPipelineState(pipeline.Get());list->SetGraphicsRootSignature(root.Get());D3D12_VIEWPORT viewport{0,0,257,259,0,1};D3D12_RECT scissor{0,0,257,259};list->RSSetViewports(1,&viewport);list->RSSetScissorRects(1,&scissor);list->OMSetRenderTargets(1,&rtv,FALSE,nullptr);list->ClearRenderTargetView(rtv,clear.Color,0,nullptr);list->IASetPrimitiveTopology(D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST);list->DrawInstanced(3,1,0,0);
 assert(SUCCEEDED(list->Close()));assert(bridge.ready());assert(bridge.arm(101));ID3D12CommandList* commands[]={list.Get()};queue->ExecuteCommandLists(1,commands);

 assert(bridge.stop());
 bool restarted=false;const auto retryUntil=GetTickCount64()+5000;
 while(!restarted&&GetTickCount64()<retryUntil){restarted=bridge.start(257,259);if(!restarted)Sleep(1);}
 assert(restarted);assert(bridge.stop());puts("PASS: stop with queued GPU work, deferred lifetime, restart");

 Readback readback;assert(readback.init(device.Get(),queue.Get()));auto submit=[](ID3D12CommandQueue* q,UINT n,ID3D12CommandList*const* lists){q->ExecuteCommandLists(n,lists);};
 assert(readback.submit(target.Get(),D3D12_RESOURCE_STATE_RENDER_TARGET,128,129,1,submit));
 assert(readback.submit(target.Get(),D3D12_RESOURCE_STATE_RENDER_TARGET,1,1,2,submit));
 assert(readback.submit(target.Get(),D3D12_RESOURCE_STATE_RENDER_TARGET,128,129,3,submit));
 assert(!readback.submit(target.Get(),D3D12_RESOURCE_STATE_RENDER_TARGET,128,129,4,submit));
 unsigned done=0;const auto deadline=GetTickCount64()+5000;while(done<3&&GetTickCount64()<deadline){float depth=0;const auto id=readback.poll(depth);if(id){assert(depth==(id==2?7.f:42.f));++done;printf("fence-complete result %llu: %g\n",id,depth);}else Sleep(1);}
 assert(done==3&&readback.idle());puts("PASS: triangle coverage, empty pixel, independent slots, backpressure, fence-gated readback");
}
