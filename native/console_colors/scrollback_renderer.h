#pragma once
#include "semantic_colors.h"
#include <cmath>
#include <cstdint>
namespace ConsoleScrollback {
using ConsoleRenderClone::Color;
struct Frame { float width,height,dpi=1,opacity_percent=75,x=0,bottom=0,sample_height=0; std::int32_t count=0,newest=0,scroll=0; bool safe_zone=false; };
struct Line { const wchar_t* data=nullptr; std::size_t count=0; };
struct Authority { bool same_session=false,same_console=false,game_thread=false,attachment_valid=false,abi_verified=false; };
inline bool admitted(const Authority& a) { return a.same_session && a.same_console && a.game_thread && a.attachment_valid && a.abi_verified; }
// Ops must capture/prevalidate all metadata before background emits, since fallback
// after partial drawing would composite the original renderer twice.
// Drawing uses engine-owned font/Canvas helpers; no binary instructions are copied.
template<class Ops> bool render(const Authority& authority,const Frame& f,Ops& ops) {
 if(!admitted(authority)) { ops.original(); return false; }
 if(!std::isfinite(f.dpi) || f.dpi<=0 || !std::isfinite(f.sample_height) || f.sample_height<=0 || !std::isfinite(f.width) || !std::isfinite(f.height) || f.width<=0 || f.height<=0 || f.count<0 || f.count>65536 || f.scroll<0 || !ops.prevalidate(f)) { ops.original(); return false; }
 if(!std::isfinite(f.x) || !std::isfinite(f.opacity_percent) || f.x<-2147480000.0f || f.x>2147480000.0f) { ops.original(); return false; }
 const float scale=1/f.dpi;
 const float row=f.sample_height*scale;
 const float bottom=f.safe_zone?f.bottom:std::floor(f.height*0.75f);
 if(!std::isfinite(bottom) || !std::isfinite(row) || row<=0 || bottom<-2147480000.0f || bottom>2147480000.0f) { ops.original(); return false; }
 ops.background(f.x,0,f.width,bottom,f.opacity_percent*0.01f);
 float y=bottom-row;
 std::int64_t index=std::int64_t(f.newest)-f.scroll;
 std::uint32_t visited=0;
 while(y>-row && index>=0 && visited++<65536) {
  if(index<f.count) {
   const auto line=ops.line(static_cast<std::int32_t>(index));
   const float measured=ops.measure_height(line)*scale;
   if(measured>row) y-=measured-row;
   ops.text(line,f.x,y,scale,ConsoleRenderClone::classify(line.data,line.count));
  }
  y-=row;--index;
 }
 // Native helper's exact baseline derives separately from bottom plus engine
 // constant, not the final scrollback y. Ops preserves that original calculation.
 ops.original_input(f.x,bottom);
 return true;
}
}
