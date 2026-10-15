#define NOMINMAX
#include <windows.h>
#include <wincodec.h>
#include <wrl/client.h>
#include <vector>
#include <cmath>
#include <algorithm>
using Microsoft::WRL::ComPtr;
static HRESULT read(IWICImagingFactory* factory,const wchar_t* path,std::vector<BYTE>& rgb) {
    WIN32_FILE_ATTRIBUTE_DATA info{};
    if(!GetFileAttributesExW(path,GetFileExInfoStandard,&info)||info.nFileSizeHigh||info.nFileSizeLow>4*1024*1024)return E_INVALIDARG;
    const size_t length=wcslen(path);
    if(length>=4&&!wcscmp(path+length-4,L".rgb")) {
        if(info.nFileSizeLow!=320*240*3)return E_INVALIDARG;
        HANDLE file=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);if(file==INVALID_HANDLE_VALUE)return E_FAIL;
        rgb.resize(320*240*3);DWORD readBytes=0;const bool ok=ReadFile(file,rgb.data(),DWORD(rgb.size()),&readBytes,nullptr)&&readBytes==rgb.size();CloseHandle(file);return ok?S_OK:E_FAIL;
    }
    ComPtr<IWICBitmapDecoder> decoder;HRESULT hr=factory->CreateDecoderFromFilename(path,nullptr,GENERIC_READ,WICDecodeMetadataCacheOnDemand,&decoder);if(FAILED(hr))return hr;
    ComPtr<IWICBitmapFrameDecode> frame;hr=decoder->GetFrame(0,&frame);if(FAILED(hr))return hr;
    UINT width=0,height=0;hr=frame->GetSize(&width,&height);if(FAILED(hr)||width!=320||height!=240)return E_INVALIDARG;
    ComPtr<IWICFormatConverter> convert;hr=factory->CreateFormatConverter(&convert);if(FAILED(hr))return hr;
    hr=convert->Initialize(frame.Get(),GUID_WICPixelFormat24bppRGB,WICBitmapDitherTypeNone,nullptr,0,WICBitmapPaletteTypeCustom);if(FAILED(hr))return hr;
    rgb.resize(320*240*3);return convert->CopyPixels(nullptr,960,UINT(rgb.size()),rgb.data());
}
static HRESULT write(IWICImagingFactory* factory,const wchar_t* path,const std::vector<BYTE>& rgb) {
    ComPtr<IWICStream> stream;HRESULT hr=factory->CreateStream(&stream);if(FAILED(hr))return hr;
    hr=stream->InitializeFromFilename(path,GENERIC_WRITE);if(FAILED(hr))return hr;
    ComPtr<IWICBitmapEncoder> encoder;hr=factory->CreateEncoder(GUID_ContainerFormatPng,nullptr,&encoder);if(FAILED(hr))return hr;
    hr=encoder->Initialize(stream.Get(),WICBitmapEncoderNoCache);if(FAILED(hr))return hr;
    ComPtr<IWICBitmapFrameEncode> frame;hr=encoder->CreateNewFrame(&frame,nullptr);if(FAILED(hr))return hr;
    hr=frame->Initialize(nullptr);if(FAILED(hr))return hr;
    hr=frame->SetSize(320,240);if(FAILED(hr))return hr;
    auto format=GUID_WICPixelFormat24bppBGR;hr=frame->SetPixelFormat(&format);if(FAILED(hr)||format!=GUID_WICPixelFormat24bppBGR)return E_FAIL;
    auto bgr=rgb;for(size_t i=0;i<bgr.size();i+=3)std::swap(bgr[i],bgr[i+2]);
    hr=frame->WritePixels(240,960,UINT(rgb.size()),bgr.data());if(FAILED(hr))return hr;
    hr=frame->Commit();if(FAILED(hr))return hr;return encoder->Commit();
}
extern "C" __declspec(dllexport) HRESULT __cdecl compose_thumbnail(const wchar_t* basePath,const wchar_t* normalPath,const wchar_t* outputPath) {
    const HRESULT initialized=CoInitializeEx(nullptr,COINIT_MULTITHREADED);if(FAILED(initialized))return initialized;
    HRESULT result=E_FAIL;
    try {
        ComPtr<IWICImagingFactory> factory;
        result=CoCreateInstance(CLSID_WICImagingFactory,nullptr,CLSCTX_INPROC_SERVER,IID_PPV_ARGS(&factory));
        if(SUCCEEDED(result)) {
            std::vector<BYTE> base,normal,out(320*240*3);
            result=read(factory.Get(),basePath,base);
            if(SUCCEEDED(result))result=read(factory.Get(),normalPath,normal);
            if(SUCCEEDED(result)) {
                double gamma[256],normals[256];for(int v=0;v<256;++v){gamma[v]=255*std::pow(v/255.,1/2.2);normals[v]=v/127.5-1;}
                const double len=std::sqrt(.65*.65+.35*.35+.68*.68),lx=-.65/len,ly=-.35/len,lz=.68/len;
                for(size_t i=0;i<base.size();i+=3) {
                    if(!(base[i]|base[i+1]|base[i+2]|normal[i]|normal[i+1]|normal[i+2])){out[i]=42;out[i+1]=46;out[i+2]=53;continue;}
                    const double x=normals[normal[i]],y=normals[normal[i+1]],z=normals[normal[i+2]];
                    const double shade=.75+.25*std::max(0.,(x*lx+y*ly+z*lz)/std::max(.001,std::sqrt(x*x+y*y+z*z)));
                    for(int j=0;j<3;++j)out[i+j]=BYTE(std::clamp(std::nearbyint(gamma[base[i+j]]*shade),0.,255.));
                }
                result=write(factory.Get(),outputPath,out);
            }
        }
    } catch(...) {result=E_FAIL;}
    CoUninitialize();return result;
}

