#pragma once
#include "native_adapter.h"
#include <vector>
namespace ConsoleNativeTarget {
using namespace ConsoleNativeAdapter;
struct Reader {
 bool(*copy)(std::uintptr_t,void*,std::size_t)=nullptr;
 bool(*span)(std::uintptr_t,std::size_t)=nullptr;
 template<class T> bool get(std::uintptr_t at,T& value)const{return copy && copy(at,&value,sizeof(value));}
};
// Hash verifier must verify the complete local image and all listed helper ranges
// against helper-proof.json before invoking bind. No native Session is inferred.
struct VerifiedImage {
 std::uintptr_t base=0;
 bool(*exact_shipping_image)(std::uintptr_t)=nullptr;
};
inline Api bind(const VerifiedImage& proof,const Reader& reader) {
 Api a;const auto b=proof.base;
 if(!b || !proof.exact_shipping_image || !proof.exact_shipping_image(b))return a;
 a.measure_font=reinterpret_cast<GetFont>(b+0x3d8c8d0);a.draw_font=reinterpret_cast<GetFont>(b+0x3d8ba90);
 a.measure=reinterpret_cast<Measure>(b+0x3de7f30);a.from_string=reinterpret_cast<FromString>(b+0x10b9050);
 a.move_text=reinterpret_cast<MoveText>(b+0x10a65f0);a.construct_text=reinterpret_cast<ConstructText>(b+0x2823bd0);
 a.destroy_text=reinterpret_cast<DestroyText>(b+0x3dbe9f0);a.texture_resource=reinterpret_cast<TextureResource>(b+0x3d632a0);
 a.draw_tile=reinterpret_cast<DrawTile>(b+0x3dc9720);a.flush=reinterpret_cast<Flush>(b+0x3dd1e10);
 a.original=reinterpret_cast<Original>(b+0x3ddf4b0);a.input=reinterpret_cast<Input>(b+0x3ddfab0);
 a.tile_vtable=b+0x7816f28;
 if(!reader.copy || !reader.copy(b+0x905b450,a.tile_uv1.data(),16))return Api{};
 return a;
}
struct Captured {
 Snapshot snapshot;std::vector<String> lines;
 // Contains only borrowed current-frame views; never retain across callback.
 Captured()=default;Captured(const Captured&)=delete;Captured& operator=(const Captured&)=delete;
};
inline bool capture(const Authority& authority,const VerifiedImage& image,const Reader& r,Api& api,std::uintptr_t console,std::uintptr_t canvas_object,Captured& out) {
 if(!ConsoleScrollback::admitted(authority) || !api.ready() || !r.copy || !r.span || !console || !canvas_object)return false;
 Snapshot s;auto& f=s.frame;std::uintptr_t canvas=0,settings=0,texture=0,data=0;
 if(!r.get(canvas_object+0x2e0,canvas) || !canvas || !r.get(console+0x118,settings) || !settings || !r.get(console+0x40,texture) || !texture || !r.get(console+0x50,data) || !r.get(console+0x58,f.count) || !r.get(console+0x5c,s.capacity) || !r.get(console+0x60,f.newest) || !r.get(console+0x64,f.scroll) || !r.get(canvas_object+0x30,f.width) || !r.get(canvas_object+0x34,f.height) || !r.get(settings+0x50,f.opacity_percent))return false;
 std::uint8_t no_dpi=0;if(!r.get(canvas+0xa0,no_dpi) || (!no_dpi && !r.get(canvas+0xb0,f.dpi)))return false;
 if(no_dpi)f.dpi=1;
 // These two original helpers select the appropriate console-variable shadow
 // value. Preserve the shipping test/order instead of assuming main-thread slot.
 using BoolFn=bool(*)();const auto b=image.base;
 const auto thread_a=reinterpret_cast<BoolFn>(b+0x1087760);const auto thread_b=reinterpret_cast<BoolFn>(b+0x1087720);
 const auto cvar=[&](std::uintptr_t global,std::int32_t& value){std::uintptr_t p=0;if(!r.get(b+global,p) || !p)return false;const std::size_t off=(thread_a() || thread_b())?0:4;return r.get(p+off,value);};
 std::int32_t enabled=0;if(!cvar(0x94dfb70,enabled))return false;
 if(enabled) {
  std::int32_t x=0,y=0;if(!cvar(0x94dfb88,x) || !cvar(0x94dfba0,y))return false;
  f.safe_zone=true;f.x=float(x);f.bottom=f.height-float(y);
 }
 if(f.count<0 || f.count>s.capacity || s.capacity<0 || s.capacity>65536 || f.scroll<0 || !std::isfinite(f.dpi) || f.dpi<=0)return false;
 out.lines.resize(std::size_t(f.count));
 if(f.count && (!data || !r.copy(data,out.lines.data(),out.lines.size()*sizeof(String))))return false;
 for(const auto& line:out.lines) {
  if(line.count<0 || line.count>32769 || line.capacity<line.count || line.capacity>1048576)return false;
  if(line.count) {
   wchar_t last=1;if(!line.data || !r.span(reinterpret_cast<std::uintptr_t>(line.data),std::size_t(line.count)*sizeof(wchar_t)) || !r.get(reinterpret_cast<std::uintptr_t>(line.data+line.count-1),last) || last!=0)return false;
  }
 }
 std::uint8_t bgra[4];if(!r.copy(settings+0x58,bgra,4))return false;
 // The initial ctor color is overwritten before any scrollback draw; retain
 // alpha here, since no exact sRGB lookup is needed for an unrendered value.
 s.initial_color={1,1,1,float(bgra[3])/255};
 auto font=api.measure_font();if(!font)return false;
 const wchar_t sample[]=L"M";const String sample_string{sample,2,2};float width=0,height=0;
 api.measure(font,&sample_string,&width,&height,true,reinterpret_cast<void*>(canvas));f.sample_height=height;
 s.console=reinterpret_cast<void*>(console);s.canvas_object=reinterpret_cast<void*>(canvas_object);s.canvas=reinterpret_cast<void*>(canvas);s.texture=reinterpret_cast<void*>(texture);s.lines=out.lines.data();s.proof=true;out.snapshot=s;return true;
}
}
