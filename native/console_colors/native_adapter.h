#pragma once
#include "scrollback_renderer.h"
#include <array>
#include <cstring>
#include <stdexcept>
namespace ConsoleNativeAdapter {
using Color=ConsoleRenderClone::Color;
using ConsoleScrollback::Frame;using ConsoleScrollback::Line;using ConsoleScrollback::Authority;
struct String { const wchar_t* data; std::int32_t count,capacity; };
struct Text { void* shared=nullptr; std::uint32_t flags=0,padding=0; };
struct Vec2 { double x,y; };
static_assert(sizeof(String)==16 && sizeof(Text)==16 && sizeof(Color)==16 && sizeof(Vec2)==16,"shipping ABI");
using GetFont=void*(*)();
using Measure=void(*)(void*,const String*,float*,float*,bool,void*);
using FromString=Text*(*)(Text*,const String*);
using MoveText=Text*(*)(Text*,Text*);
using ConstructText=void*(*)(void*,const Vec2*,const Text*,void*,const Color*);
using DestroyText=void(*)(void*);
using TextureResource=void*(*)(void*);
using DrawTile=void(*)(void*,void*);
using Flush=void(*)(void*,bool);
using Original=void(*)(void*,void*);
using Input=void(*)(void*,void*,std::uint64_t);
using DrawText=void(*)(void*,void*,float,float);
using ReleaseShared=void(*)(void*);
struct Api {
 GetFont measure_font=nullptr,draw_font=nullptr;Measure measure=nullptr;
 FromString from_string=nullptr;MoveText move_text=nullptr;ConstructText construct_text=nullptr;DestroyText destroy_text=nullptr;
 TextureResource texture_resource=nullptr;DrawTile draw_tile=nullptr;Flush flush=nullptr;Original original=nullptr;Input input=nullptr;
 bool(*can_create)()=nullptr;bool(*can_release)()=nullptr;bool(*known_text)(const Text&)=nullptr;void(*release_text)(Text&)=nullptr;bool(*known_item)(const void*)=nullptr;
 std::uintptr_t tile_vtable=0;std::array<std::byte,16> tile_uv1{};
 bool ready()const {return measure_font && draw_font && measure && from_string && move_text && construct_text && destroy_text && texture_resource && draw_tile && flush && original && input && tile_vtable && can_create && can_release && known_text && release_text && known_item;}
};
template<class T> inline T load(const void* at) { T v;std::memcpy(&v,at,sizeof(v));return v; }
template<class T> inline void store(void* base,std::size_t off,const T& v){std::memcpy(static_cast<std::byte*>(base)+off,&v,sizeof(v));}
enum class State { Empty, Live, Unknown };
struct RenderStorage {
 Text temporary{};State temporary_state=State::Empty,item_state=State::Empty;
 alignas(8) std::array<std::byte,544> item{};
 bool emitted=false;
 // Caller retains this storage for the entire pinned instance. No implicit
 // destructor cleanup; Unknown states must remain quarantined, never replayed.
};
struct Tile { alignas(16) std::array<std::byte,176> bytes{}; };
inline Tile background_item(const Api& api,float x,float width,float extent,float opacity,void* texture) {
 Tile t;auto p=t.bytes.data();store(p,0,api.tile_vtable);store(p,8,Vec2{double(x),0});
 store(p,28,std::uint32_t(11));store(p,60,opacity);store(p,64,Vec2{double(width),double(extent)});
 store(p,80,1.0f);store(p,104,Vec2{1,1});store(p,120,texture);std::memcpy(p+160,api.tile_uv1.data(),16);return t;
}
// Immutable snapshot obtained on the verified GameThread before emitting draws.
// read/probe validation and Session/console identities are supplied by the owner.
struct Snapshot {
 Frame frame;void* console=nullptr;void* canvas_object=nullptr;void* canvas=nullptr;void* texture=nullptr;
 const String* lines=nullptr;std::int32_t capacity=0;Color initial_color=ConsoleRenderClone::white;
 // This is the exact original font DPI mode, not a fixed screen-pixel scale.
 bool proof=false;
};
class Adapter {
 Api& api_;const Snapshot& s_;RenderStorage& storage_;void* measure_font_=nullptr;void* draw_font_=nullptr;
 void fail(){throw std::runtime_error("Console render ownership uncertain");}
 void release_temporary() {
  if(storage_.temporary_state==State::Empty)return;
  if(storage_.temporary_state!=State::Live || !api_.can_release() || !api_.known_text(storage_.temporary))fail();
  storage_.temporary_state=State::Unknown;api_.release_text(storage_.temporary);storage_.temporary={};storage_.temporary_state=State::Empty;
 }
 void destroy_item() {
  if(storage_.item_state==State::Empty)return;
  if(storage_.item_state!=State::Live || !api_.can_release() || !api_.known_item(storage_.item.data()))fail();
  storage_.item_state=State::Unknown;api_.destroy_text(storage_.item.data());storage_.item_state=State::Empty;
 }
public:
 Adapter(Api& api,const Snapshot& s,RenderStorage& storage):api_(api),s_(s),storage_(storage){}
 void original(){api_.original(s_.console,s_.canvas_object);}
 bool prevalidate(const Frame& f) {
  if(!s_.proof || !api_.ready() || !api_.can_create() || storage_.temporary_state!=State::Empty || storage_.item_state!=State::Empty || !s_.canvas || !s_.canvas_object || !s_.console || !s_.texture || f.count>s_.capacity || s_.capacity<0 || s_.capacity>65536 || (f.count && !s_.lines))return false;
  measure_font_=api_.measure_font();draw_font_=api_.draw_font();if(!measure_font_ || !draw_font_)return false;
  for(std::int32_t i=0;i<f.count;++i) {
   const auto& str=s_.lines[i];if(str.count<0 || str.count>32769 || str.capacity<str.count || str.capacity>1048576 || (str.count && (!str.data || str.data[str.count-1]!=0)))return false;
  }
  storage_.emitted=false;return true;
 }
 void background(float x,float,float width,float bottom,float alpha) {
  const float row=s_.frame.sample_height/s_.frame.dpi;
  auto tile=background_item(api_,x,width,bottom-row,alpha,api_.texture_resource(s_.texture));
  storage_.emitted=true;api_.draw_tile(tile.bytes.data(),s_.canvas);flush_if_needed();
 }
 Line line(std::int32_t i){const auto& l=s_.lines[i];return {l.data,l.count?std::size_t(l.count-1):0};}
 float measure_height(Line line){String str{line.data,std::int32_t(line.data?line.count+1:0),std::int32_t(line.data?line.count+1:0)};float w=0,h=0;api_.measure(measure_font_,&str,&w,&h,true,s_.canvas);if(!std::isfinite(h) || h<0)fail();return h;}
 void text(Line line,float x,float y,float,Color color) {
  if(!api_.can_create() || storage_.temporary_state!=State::Empty)fail();
  String str{line.data,std::int32_t(line.data?line.count+1:0),std::int32_t(line.data?line.count+1:0)};
  storage_.temporary_state=State::Unknown;api_.from_string(&storage_.temporary,&str);
  if(!api_.known_text(storage_.temporary))fail();storage_.temporary_state=State::Live;
  if(storage_.item_state==State::Empty) {
   const Vec2 initial{double(x),double(y)};storage_.item_state=State::Unknown;
   api_.construct_text(storage_.item.data(),&initial,&storage_.temporary,draw_font_,&s_.initial_color);
   if(!api_.known_item(storage_.item.data()))fail();storage_.item_state=State::Live;
  } else {
   if(storage_.item_state!=State::Live || !api_.known_item(storage_.item.data()))fail();
   storage_.item_state=State::Unknown;storage_.temporary_state=State::Unknown;
   api_.move_text(reinterpret_cast<Text*>(storage_.item.data()+0x198),&storage_.temporary);
   if(!api_.known_item(storage_.item.data()) || !api_.known_text(storage_.temporary))fail();
   storage_.item_state=State::Live;storage_.temporary_state=State::Live;
  }
  release_temporary();store(storage_.item.data(),0x30,color);
  auto table=load<std::uintptr_t*>(storage_.item.data());storage_.item_state=State::Unknown;reinterpret_cast<DrawText>(table[1])(storage_.item.data(),s_.canvas,x,y);storage_.item_state=State::Live;flush_if_needed();
 }
 void original_input(float x,float bottom) {
  destroy_item();release_temporary();
  const std::int32_t xy[2]={static_cast<std::int32_t>(x),static_cast<std::int32_t>(bottom+6.0f)};
  api_.input(s_.console,s_.canvas_object,load<std::uint64_t>(xy));
 }
 void flush_if_needed(){if(load<std::int32_t>(static_cast<std::byte*>(s_.canvas)+0xac)==1)api_.flush(s_.canvas,false);}
};
inline bool render(const Authority& authority,Api& api,const Snapshot& snapshot,RenderStorage& storage) {
 if(!api.original)return false;Adapter adapter(api,snapshot,storage);return ConsoleScrollback::render(authority,snapshot.frame,adapter);
}
}
