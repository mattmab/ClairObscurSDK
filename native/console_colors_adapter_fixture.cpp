#include "console_colors/native_adapter.h"
#include <cassert>
#include <vector>
using namespace ConsoleNativeAdapter;
static int constructed=0,destroyed=0,froms=0,released=0,inputs=0,originals=0,tiles=0,flushes=0;
static float expected_tile_height=790;
static std::vector<Color> colors;static std::vector<float> ys;static std::uint64_t input_xy=0;
struct Shared {std::uintptr_t* table;int refs=1;};
void retain(void* s){++static_cast<Shared*>(s)->refs;}
void release_shared(void* s){auto p=static_cast<Shared*>(s);if(!--p->refs){++released;delete p;}}
std::uintptr_t shared_table[3]={0,reinterpret_cast<std::uintptr_t>(&retain),reinterpret_cast<std::uintptr_t>(&release_shared)};
static bool draw_fault=false,destroy_fault=false;
void draw(void* item,void*,float,float y){colors.push_back(load<Color>(static_cast<std::byte*>(item)+0x30));ys.push_back(y);if(draw_fault)throw std::runtime_error("draw uncertainty");}
std::uintptr_t draw_table[2]={0,reinterpret_cast<std::uintptr_t>(&draw)};
void* font(){return reinterpret_cast<void*>(1);}
void measure(void*,const String* s,float* w,float* h,bool flag,void*){assert(flag);*w=10;*h=s->count==14?40.0f:20.0f;}
Text* from(Text* t,const String*){++froms;t->shared=new Shared{shared_table};return t;}
void release(Text& t){if(t.shared){release_shared(t.shared);t.shared=nullptr;}}
Text* move(Text* d,Text* s){release(*d);*d=*s;s->shared=new Shared{shared_table};return d;}
void* ctor(void* p,const Vec2*,const Text* t,void*,const Color*){++constructed;store(p,0,reinterpret_cast<std::uintptr_t>(draw_table));store(p,0x198,*t);retain(t->shared);return p;}
void dtor(void* p){if(destroy_fault)throw std::runtime_error("destructor uncertainty");++destroyed;release(*reinterpret_cast<Text*>(static_cast<std::byte*>(p)+0x198));}
void* resource(void* p){return p;}
void tile(void* p,void*){++tiles;assert(load<std::uint32_t>(static_cast<std::byte*>(p)+28)==11);assert(load<float>(static_cast<std::byte*>(p)+60)==0.75f);assert(load<Vec2>(static_cast<std::byte*>(p)+64).y==expected_tile_height);}
void flush(void*,bool f){assert(!f);++flushes;}
static bool fallback_started=false;
void original(void*,void*){fallback_started=true;++originals;}
void original_throws(void*,void*){fallback_started=true;++originals;throw std::runtime_error("fixture original failed");}
void input(void*,void*,std::uint64_t xy){++inputs;input_xy=xy;assert(constructed==destroyed);}
bool yes(){return true;}
bool known_text(const Text& t){return t.shared && load<std::uintptr_t*>(t.shared)==shared_table;}
bool known_item(const void* p){return load<std::uintptr_t*>(p)==draw_table;}
Text* from_fault(Text* t,const String* s){from(t,s);throw std::runtime_error("fixture constructor unknown");}
int main(){
 Api a;a.measure_font=font;a.draw_font=font;a.measure=measure;a.from_string=from;a.move_text=move;a.construct_text=ctor;a.destroy_text=dtor;a.texture_resource=resource;a.draw_tile=tile;a.flush=flush;a.original=original;a.input=input;a.tile_vtable=42;a.can_create=yes;a.can_release=yes;a.known_text=known_text;a.release_text=release;a.known_item=known_item;
 std::array<std::byte,0x100> canvas{};store(canvas.data(),0xac,std::int32_t(1));
 const String lines[]={{L"Engine",7,7},{L"[READY] ready",14,14},{L"Other",6,6}};
 Snapshot s;s.frame.width=1920;s.frame.height=1080;s.frame.sample_height=20;s.frame.count=3;s.frame.newest=2;s.capacity=3;s.console=reinterpret_cast<void*>(1);s.canvas_object=reinterpret_cast<void*>(2);s.canvas=canvas.data();s.texture=reinterpret_cast<void*>(3);s.lines=lines;s.proof=true;
 RenderStorage storage;Authority auth{true,true,true,true,true};assert(render(auth,a,s,storage));
 assert(tiles==1 && constructed==1 && destroyed==1 && froms==3 && released==5 && inputs==1 && originals==0 && flushes==4);
 assert(colors.size()==3 && colors[0].r==1 && colors[1].g==ConsoleRenderClone::green.g && colors[2].r==1);
 assert(ys[0]==790 && ys[1]==750 && ys[2]==730);
 std::int32_t xy[2];std::memcpy(xy,&input_xy,8);assert(xy[0]==0 && xy[1]==816);
 s.proof=false;assert(!render(auth,a,s,storage));assert(originals==1 && tiles==1 && inputs==1);
 s.proof=true;a.from_string=from_fault;RenderStorage uncertain;
 bool threw=false;try{render(auth,a,s,uncertain);}catch(const std::runtime_error&){threw=true;}
 assert(threw && uncertain.temporary_state==State::Unknown && uncertain.item_state==State::Empty);
 const int before=froms;assert(!render(auth,a,s,uncertain));assert(froms==before);
 // Fixture-only allocation cleanup; production retains unknown state pinned.
 release_shared(uncertain.temporary.shared);uncertain.temporary.shared=nullptr;
 a.from_string=from;
 a.original=original_throws;const int original_before=originals;fallback_started=false;s.proof=false;
 try{render(auth,a,s,storage);}catch(...){if(!fallback_started && !storage.emitted)original_throws(s.console,s.canvas);}
 assert(originals==original_before+1);a.original=original;s.proof=true;
 s.proof=true;const String bad[]={{nullptr,1,1}};s.lines=bad;s.frame.count=1;s.capacity=1;assert(!render(auth,a,s,storage));assert(originals==4 && tiles==2);
 // Native backend DPI and safe-zone placement, background and packed input.
 s.lines=lines;s.frame.count=3;s.capacity=3;s.frame.dpi=2;expected_tile_height=800;
 const auto y_start=ys.size();RenderStorage dpi_storage;assert(render(auth,a,s,dpi_storage));
 assert(ys[y_start]==800 && ys[y_start+1]==780 && ys[y_start+2]==770);
 s.frame.dpi=1;s.frame.safe_zone=true;s.frame.x=8;s.frame.bottom=1000;expected_tile_height=980;
 const auto safe_start=ys.size();RenderStorage safe_storage;assert(render(auth,a,s,safe_storage));
 assert(ys[safe_start]==980 && ys[safe_start+1]==940 && ys[safe_start+2]==920);
 std::memcpy(xy,&input_xy,8);assert(xy[0]==8 && xy[1]==1006);
 // Native draw/destructor uncertainty remains pinned and cannot be replayed.
 draw_fault=true;RenderStorage draw_unknown;const int original_count=originals;
 try{render(auth,a,s,draw_unknown);}catch(const std::runtime_error&){}
 assert(draw_unknown.item_state==State::Unknown && draw_unknown.emitted);
 assert(originals==original_count);draw_fault=false;
 // Fixture-only reclamation of known fake memory, not a production retry.
 release(*reinterpret_cast<Text*>(draw_unknown.item.data()+0x198));
 destroy_fault=true;RenderStorage destructor_unknown;
 try{render(auth,a,s,destructor_unknown);}catch(const std::runtime_error&){}
 assert(destructor_unknown.item_state==State::Unknown && destructor_unknown.emitted);
 assert(originals==original_count);destroy_fault=false;
 release(*reinterpret_cast<Text*>(destructor_unknown.item.data()+0x198));

}
